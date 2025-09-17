import os
from docling.document_converter import DocumentConverter
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
import json
import pandas as pd
import csv
import streamlit as st
import tempfile

def load_llm(id_model, temperature):
    """
    Carrega o modelo LLM com tratamento de erro para chave API
    
    Args:
        id_model (str): ID do modelo a ser usado
        temperature (float): Temperatura para criatividade do modelo
    
    Returns:
        ChatGroq: Instância do modelo configurado
    """
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            st.error("❌ Chave GROQ_API_KEY não encontrada nas variáveis de ambiente!")
            st.info("Configure a chave API nas configurações do Streamlit Cloud em Settings → Secrets")
            st.stop()
            
        llm = ChatGroq(
            model=id_model,
            temperature=temperature,
            max_tokens=None,
            timeout=60,
            max_retries=3,
            api_key=api_key
        )
        return llm
    except Exception as e:
        st.error(f"❌ Erro ao carregar modelo LLM: {str(e)}")
        st.stop()

def format_res(res, return_thinking=False):
    """
    Formata a resposta do modelo LLM removendo tags de pensamento
    
    Args:
        res (str): Resposta bruta do modelo
        return_thinking (bool): Se deve manter o conteúdo de pensamento
    
    Returns:
        str: Resposta formatada
    """
    res = res.strip()
    if return_thinking:
        res = res.replace("
<details type="reasoning" done="true" duration="0">
<summary>Thought for 0 seconds</summary>
> ", "[pensando...] ")
>         res = res.replace("
</details>
", "\n---\n")
    else:
        if "</think>" in res:
            res = res.split("</think>")[-1].strip()
    return res

def parse_doc(file_path):
    """
    Converte documento PDF para markdown usando Docling
    
    Args:
        file_path (str): Caminho para o arquivo PDF
    
    Returns:
        str: Conteúdo do documento em markdown ou None se erro
    """
    try:
        if not os.path.exists(file_path):
            st.error(f"❌ Arquivo não encontrado: {file_path}")
            return None
            
        # Verifica tamanho do arquivo (máximo 10MB)
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            st.error("❌ Arquivo muito grande. Máximo permitido: 10MB")
            return None
            
        converter = DocumentConverter()
        result = converter.convert(file_path)
        content = result.document.export_to_markdown()
        
        if not content or len(content.strip()) < 50:
            st.warning("⚠️ Pouco conteúdo extraído do documento. Verifique se o PDF não está corrompido.")
            
        return content
        
    except Exception as e:
        st.error(f"❌ Erro ao processar documento: {str(e)}")
        st.info("Certifique-se de que o arquivo é um PDF válido e não está protegido por senha.")
        return None

def parse_res_llm(response_text: str, required_fields: list) -> dict:
    """
    Faz o parsing da resposta do LLM extraindo dados estruturados JSON
    
    Args:
        response_text (str): Resposta bruta do modelo
        required_fields (list): Lista de campos obrigatórios
    
    Returns:
        dict: Dados estruturados extraídos
    """
    try:
        # Remove a parte do raciocínio se existir
        if "</think>" in response_text:
            response_text = response_text.split("</think>")[-1].strip()
        
        # Localiza o JSON na resposta
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise json.JSONDecodeError("Nenhum JSON encontrado na resposta", response_text, 0)
        
        json_str = response_text[start_idx:end_idx]
        info_cv = json.loads(json_str)
        
        # Garante que todos os campos obrigatórios existem
        list_fields = ['skills', 'interview_questions', 'strengths', 'areas_for_development', 'important_considerations']
        for field in required_fields:
            if field not in info_cv:
                if field in list_fields:
                    info_cv[field] = []
                elif field == 'score':
                    info_cv[field] = 0.0
                else:
                    info_cv[field] = ""
        
        # Validação básica dos dados
        if not info_cv.get('name') or not info_cv.get('name').strip():
            st.warning("⚠️ Nome do candidato não foi identificado corretamente.")
            info_cv['name'] = "Candidato sem nome identificado"
            
        # Garante que score é numérico
        try:
            info_cv['score'] = float(info_cv.get('score', 0))
            if info_cv['score'] < 0:
                info_cv['score'] = 0.0
            elif info_cv['score'] > 10:
                info_cv['score'] = 10.0
        except (ValueError, TypeError):
            info_cv['score'] = 0.0
            
        return info_cv
        
    except json.JSONDecodeError as e:
        st.error(f"❌ Erro ao interpretar resposta da IA: {str(e)}")
        st.info("O modelo retornou uma resposta mal formatada. Tentando novamente...")
        return create_default_cv_data(required_fields)
    except Exception as e:
        st.error(f"❌ Erro inesperado no parsing: {str(e)}")
        return create_default_cv_data(required_fields)

def create_default_cv_data(required_fields):
    """
    Cria estrutura padrão de dados do CV em caso de erro
    
    Args:
        required_fields (list): Campos obrigatórios
    
    Returns:
        dict: Estrutura padrão de dados
    """
    default_data = {}
    list_fields = ['skills', 'interview_questions', 'strengths', 'areas_for_development', 'important_considerations']
    
    for field in required_fields:
        if field in list_fields:
            default_data[field] = []
        elif field == 'score':
            default_data[field] = 0.0
        else:
            default_data[field] = ""
    
    default_data['name'] = "Erro na análise"
    default_data['summary'] = "Houve um erro na análise deste currículo"
    
    return default_data

def save_json_cv(new_data, path_json, key_name="name"):
    """
    Salva dados do CV em arquivo JSON evitando duplicatas
    
    Args:
        new_data (dict): Dados do CV para salvar
        path_json (str): Caminho do arquivo JSON
        key_name (str): Campo chave para identificar duplicatas
    
    Returns:
        bool: True se salvou com sucesso, False caso contrário
    """
    try:
        # Validação básica dos dados
        if not new_data or not new_data.get(key_name):
            st.warning("⚠️ Dados inválidos para salvar.")
            return False
            
        if not new_data.get(key_name).strip():
            st.warning("⚠️ Nome do candidato está vazio.")
            return False
            
        # Carrega dados existentes
        if os.path.exists(path_json):
            try:
                with open(path_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                st.warning("⚠️ Arquivo JSON corrompido. Criando novo arquivo.")
                data = []
        else:
            data = []
        
        # Garante que data é uma lista
        if isinstance(data, dict):
            data = [data]
        
        # Verifica duplicatas (case-insensitive)
        candidate_name = new_data.get(key_name).strip().lower()
        existing_names = [entry.get(key_name, "").strip().lower() for entry in data if entry.get(key_name)]
        
        if candidate_name in existing_names:
            st.warning(f"⚠️ Currículo de '{new_data.get(key_name)}' já foi registrado anteriormente.")
            return False
        
        # Adiciona timestamp
        from datetime import datetime
        new_data['analyzed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Adiciona e salva
        data.append(new_data)
        with open(path_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        st.success(f"✅ Currículo de '{new_data.get(key_name)}' salvo com sucesso!")
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao salvar dados: {str(e)}")
        return False

def load_json_cv(path_json):
    """
    Carrega dados dos CVs do arquivo JSON
    
    Args:
        path_json (str): Caminho do arquivo JSON
    
    Returns:
        list: Lista de CVs ou lista vazia se erro
    """
    try:
        if not os.path.exists(path_json):
            return []
            
        with open(path_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if isinstance(data, dict):
            return [data]
        
        return data if isinstance(data, list) else []
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        return []

def show_cv_result(result: dict):
    """
    Gera markdown formatado com os resultados da análise do CV
    
    Args:
        result (dict): Dados estruturados do CV
    
    Returns:
        str: String em markdown com os resultados formatados
    """
    if not result:
        return "❌ Nenhum dado disponível para exibir."
        
    md = f"### 📄 Análise Detalhada do Currículo\n\n"
    
    # Informações básicas
    if result.get("name"):
        md += f"**👤 Nome:** {result['name']}\n\n"
    
    if result.get("area"):
        md += f"**💼 Área de Atuação:** {result['area']}\n\n"
    
    # Score com indicador visual
    if result.get("score"):
        score = float(result['score'])
        if score >= 8:
            emoji = "🟢"
            nivel = "Excelente"
        elif score >= 6:
            emoji = "🟡"
            nivel = "Bom"
        elif score >= 4:
            emoji = "🟠"
            nivel = "Regular"
        else:
            emoji = "🔴"
            nivel = "Inadequado"
        
        md += f"**📊 Pontuação:** {emoji} {score}/10 - *{nivel}*\n\n"
    
    # Resumo
    if result.get("summary"):
        md += f"**📝 Resumo do Perfil:**\n{result['summary']}\n\n"
    
    # Formação
    if result.get("education"):
        md += f"**🎓 Formação Acadêmica:**\n{result['education']}\n\n"
    
    # Competências
    if result.get("skills") and isinstance(result["skills"], list) and result["skills"]:
        md += f"**🛠️ Competências Técnicas:**\n"
        for skill in result["skills"]:
            md += f"  • {skill}\n"
        md += "\n"
    
    # Pontos fortes
    if result.get("strengths") and isinstance(result["strengths"], list) and result["strengths"]:
        md += f"**✅ Pontos Fortes:**\n"
        for strength in result["strengths"]:
            md += f"  • {strength}\n"
        md += "\n"
    
    # Áreas de desenvolvimento
    if result.get("areas_for_development") and isinstance(result["areas_for_development"], list) and result["areas_for_development"]:
        md += f"**⚠️ Áreas para Desenvolvimento:**\n"
        for area in result["areas_for_development"]:
            md += f"  • {area}\n"
        md += "\n"
    
    # Pontos de atenção
    if result.get("important_considerations") and isinstance(result["important_considerations"], list) and result["important_considerations"]:
        md += f"**🔍 Pontos de Atenção:**\n"
        for consideration in result["important_considerations"]:
            md += f"  • {consideration}\n"
        md += "\n"
    
    # Perguntas sugeridas
    if result.get("interview_questions") and isinstance(result["interview_questions"], list) and result["interview_questions"]:
        md += f"**❓ Perguntas Sugeridas para Entrevista:**\n"
        for i, question in enumerate(result["interview_questions"], 1):
            md += f"  {i}. {question}\n"
        md += "\n"
    
    # Recomendações finais
    if result.get("final_recommendations"):
        md += f"**💡 Conclusão e Recomendações:**\n{result['final_recommendations']}\n\n"
    
    # Timestamp se disponível
    if result.get("analyzed_at"):
        md += f"---\n*Análise realizada em: {result['analyzed_at']}*\n"
    
    return md

def save_job_to_csv(data, filename):
    """
    Salva informações da vaga em arquivo CSV
    
    Args:
        data (dict): Dados da vaga
        filename (str): Nome do arquivo CSV
    """
    try:
        headers = ['title', 'description', 'details']
        file_exists = os.path.exists(filename)
        
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=';')
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)
            
    except Exception as e:
        st.error(f"❌ Erro ao salvar vaga: {str(e)}")

def load_job(csv_path):
    """
    Carrega informações da vaga do arquivo CSV
    
    Args:
        csv_path (str): Caminho do arquivo CSV
    
    Returns:
        str: Texto formatado com informações da vaga
    """
    try:
        if not os.path.exists(csv_path):
            return "Erro: Arquivo de vagas não encontrado"
            
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
        if df.empty:
            return "Erro: Nenhuma vaga encontrada no arquivo"
            
        job = df.iloc[-1]  # Pega a última vaga adicionada
        
        prompt_text = f"""
**Vaga: {job['title']}**

**Descrição da Vaga:**
{job['description']}

**Detalhes Completos:**
{job['details']}
        """
        return prompt_text.strip()
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar vaga: {str(e)}")
        return "Erro: Não foi possível carregar informações da vaga"

def process_cv(schema, job_details, prompt_template, prompt_score, llm, file_path):
    """
    Processa o CV completo: extrai texto, envia para IA e retorna análise
    
    Args:
        schema (str): Schema JSON esperado
        job_details (str): Detalhes da vaga
        prompt_template: Template do prompt
        prompt_score (str): Instruções para pontuação
        llm: Modelo de linguagem
        file_path (str): Caminho do arquivo CV
    
    Returns:
        tuple: (output_completo, resultado_formatado) ou (None, None) se erro
    """
    try:
        if not file_path or not os.path.exists(file_path):
            st.error(f"❌ Arquivo não encontrado: {file_path}")
            return None, None
        
        # Extrai conteúdo do documento
        content = parse_doc(file_path)
        if not content:
            st.error("❌ Não foi possível extrair conteúdo do documento")
            return None, None
        
        # Limita o tamanho do conteúdo para evitar limite de tokens
        max_content_length = 4000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n... [conteúdo truncado para análise]"
        
        # Cria a chain e processa
        chain = prompt_template | llm
        output = chain.invoke({
            "schema": schema,
            "cv": content,
            "job": job_details,
            "prompt_score": prompt_score
        })
        
        res = format_res(output.content)
        return output, res
        
    except Exception as e:
        st.error(f"❌ Erro no processamento do CV: {str(e)}")
        if "rate limit" in str(e).lower():
            st.info("⏳ Limite de taxa atingido. Aguarde alguns segundos e tente novamente.")
        elif "timeout" in str(e).lower():
            st.info("⏳ Timeout na análise. O documento pode ser muito grande ou complexo.")
        return None, None

def display_json_table(path_json):
    """
    Carrega dados JSON e converte para DataFrame
    
    Args:
        path_json (str): Caminho do arquivo JSON
    
    Returns:
        pandas.DataFrame: DataFrame com os dados ou DataFrame vazio
    """
    try:
        if not os.path.exists(path_json):
            return pd.DataFrame()
            
        with open(path_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            data = [data]
        
        df = pd.DataFrame(data)
        return df
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar tabela: {str(e)}")
        return pd.DataFrame()

def clean_old_files():
    """
    Remove arquivos temporários antigos (executar periodicamente)
    """
    try:
        temp_dir = tempfile.gettempdir()
        current_time = time.time()
        
        for filename in os.listdir(temp_dir):
            if filename.endswith('.pdf'):
                file_path = os.path.join(temp_dir, filename)
                file_age = current_time - os.path.getctime(file_path)
                
                # Remove arquivos com mais de 1 hora
                if file_age > 3600:
                    os.remove(file_path)
                    
    except Exception:
        pass  # Silencioso para não interromper a aplicação

def validate_cv_data(data):
    """
    Valida se os dados do CV estão em formato adequado
    
    Args:
        data (dict): Dados do CV
    
    Returns:
        bool: True se válidos, False caso contrário
    """
    required_fields = ['name', 'summary', 'score']
    
    if not isinstance(data, dict):
        return False
    
    for field in required_fields:
        if field not in data or not data[field]:
            return False
    
    try:
        score = float(data['score'])
        if score < 0 or score > 10:
            return False
    except (ValueError, TypeError):
        return False
    
    return True