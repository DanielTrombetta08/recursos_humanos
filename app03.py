import streamlit as st
import uuid
import os
from utils import *
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Para deploy, usar st.secrets ao invés de .env
try:
    # Primeiro tenta st.secrets (deploy)
    groq_api_key = st.secrets["GROQ_API_KEY"]
except:
    # Se não encontrar, usa .env (desenvolvimento local)
    groq_api_key = os.getenv("GROQ_API_KEY")

# Definir a variável para o Groq
os.environ["GROQ_API_KEY"] = groq_api_key

# Configuração da página
st.set_page_config(
    page_title="Triagem e Análise de Currículos", 
    page_icon="📄", 
    layout="wide"
)

# Configurações do modelo e arquivos
id_model = "deepseek-r1-distill-llama-70b"
temperature = 0.7
json_file = 'curriculos.json'
path_job_csv = "vagas.csv"

# Carrega o modelo LLM
llm = load_llm(id_model, temperature)

# Definição da vaga (hardcoded)
job = {}
job['title'] = "Desenvolvedor(a) Full Stack"
job['description'] = "Estamos em busca de um(a) Desenvolvedor(a) Full Stack para integrar o time de tecnologia da nossa empresa, atuando em projetos estratégicos com foco em soluções escaláveis e orientadas a dados. O(a) profissional será responsável por desenvolver, manter e evoluir aplicações web robustas, além de colaborar com times multidisciplinares para entregar valor contínuo ao negócio."
job['details'] = """
Atividades:
- Desenvolver e manter aplicações web em ambientes modernos, utilizando tecnologias back-end e front-end.
- Trabalhar com equipes de produto, UX e dados para entender demandas e propor soluções.
- Criar APIs, integrações e dashboards interativos.
- Garantir boas práticas de versionamento, testes e documentação.
- Participar de revisões de código, deploys e melhorias contínuas na arquitetura das aplicações.

Pré-requisitos:
- Sólidos conhecimentos em Python, JavaScript e SQL.
- Experiência prática com frameworks como React, Node.js e Django.
- Familiaridade com versionamento de código usando Git.
- Experiência com serviços de nuvem, como AWS e Google Cloud Platform.
- Capacidade de trabalhar em equipe, com boa comunicação e perfil colaborativo.

Diferenciais:
- Conhecimento em Power BI ou outras ferramentas de visualização de dados.
- Experiência anterior em ambientes ágeis (Scrum, Kanban).
- Projetos próprios, contribuições open source ou portfólio técnico disponível.
- Certificações em nuvem ou áreas relacionadas à engenharia de software.
"""

# Schema para extração de dados estruturados
schema = """
{
  "name": "Nome completo do candidato",
  "area": "Área ou setor principal que o candidato atua. Classifique em apenas uma: Desenvolvimento, Marketing, Vendas, Financeiro, Administrativo, Outros",
  "summary": "Resumo objetivo sobre o perfil profissional do candidato",
  "skills": ["competência 1", "competência 2", "..."],
  "education": "Resumo da formação acadêmica mais relevante",
  "interview_questions": ["Pelo menos 3 perguntas úteis para entrevista com base no currículo, para esclarecer algum ponto ou explorar melhor"],
  "strengths": ["Pontos fortes e aspectos que indicam alinhamento com o perfil ou vaga desejada"],
  "areas_for_development": ["Pontos que indicam possíveis lacunas, fragilidades ou necessidades de desenvolvimento"],
  "important_considerations": ["Observações específicas que merecem verificação ou cuidado adicional"],
  "final_recommendations": "Resumo avaliativo final com sugestões de próximos passos (ex: seguir com entrevista, indicar para outra vaga)",
  "score": 0.0
}
"""

# Campos obrigatórios para validação
fields = [
    "name",
    "area",
    "summary",
    "skills",
    "education",
    "interview_questions",
    "strengths",
    "areas_for_development",
    "important_considerations",
    "final_recommendations",
    "score"
]

# Critérios de pontuação
prompt_score = """
Com base na vaga específica, calcule a pontuação final (de 0.0 a 10.0).
O retorno para esse campo deve conter apenas a pontuação final (x.x) sem mais nenhum texto ou anotação.
Seja justo e rigoroso ao atribuir as notas. A nota 10.0 só deve ser atribuída para candidaturas que superem todas as expectativas da vaga.

Critérios de avaliação:
1. Experiência (Peso: 35% do total): Análise de posições anteriores, tempo de atuação e similaridade com as responsabilidades da vaga.
2. Habilidades Técnicas (Peso: 25% do total): Verifique o alinhamento das habilidades técnicas com os requisitos mencionados na vaga.
3. Educação (Peso: 15% do total): Avalie a relevância da graduação/certificações para o cargo, incluindo instituições e anos de estudo.
4. Pontos Fortes (Peso: 15% do total): Avalie a relevância dos pontos fortes (ou alinhamentos) para a vaga.
5. Pontos Fracos (Desconto de até 10%): Avalie a gravidade dos pontos fracos (ou desalinhamentos) para a vaga.
"""

# Template do prompt para análise
prompt_template = ChatPromptTemplate.from_template("""
Você é um especialista em Recursos Humanos com vasta experiência em análise de currículos.
Sua tarefa é analisar o conteúdo a seguir e extrair os dados conforme o formato abaixo, para cada um dos campos.
Responda apenas com o JSON estruturado e utilize somente essas chaves. Cuide para que os nomes das chaves sejam exatamente esses.
Não adicione explicações ou anotações fora do JSON.

Schema desejado:
{schema}

---
Para o cálculo do campo score:
{prompt_score}

---
Currículo a ser analisado:
'{cv}'

---
Vaga que o candidato está se candidatando:
'{job}'
""")

# Inicialização do estado da sessão
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())

if "selected_cv" not in st.session_state:
    st.session_state.selected_cv = None

if "show_confirm" not in st.session_state:
    st.session_state.show_confirm = False

# Salva descrição da vaga em CSV
save_job_to_csv(job, path_job_csv)
job_details = load_job(path_job_csv)

# Interface principal - Layout em duas colunas
col1, col2 = st.columns(2)

with col1:
    st.header("Triagem e Análise de Currículos")
    st.markdown("#### Vaga: {}".format(job["title"]))

with col2:
    uploaded_file = st.file_uploader(
        "Envie um currículo em PDF", 
        type=["pdf"], 
        key=st.session_state.uploader_key,
        help="Faça upload de um arquivo PDF contendo o currículo para análise"
    )

# Processamento do upload
if uploaded_file is not None:
    with st.spinner("Analisando o currículo..."):
        try:
            # Salva arquivo temporariamente
            path = uploaded_file.name
            with open(path, "wb") as f:
                f.write(uploaded_file.read())
            
            # Processa o currículo
            output, res = process_cv(schema, job_details, prompt_template, prompt_score, llm, path)
            structured_data = parse_res_llm(res, fields)
            
            # Verifica se os dados foram extraídos corretamente
            if structured_data:
                save_json_cv(structured_data, path_json=json_file, key_name="name")
                st.success("✅ Currículo analisado com sucesso!")
                st.session_state.uploader_key = str(uuid.uuid4())
                
                # Remove arquivo temporário
                try:
                    os.remove(path)
                except:
                    pass
                
            else:
                st.error("❌ Erro ao processar o currículo. Tente novamente.")
                
        except Exception as e:
            st.error(f"❌ Erro durante o processamento: {str(e)}")
            # Remove arquivo temporário em caso de erro
            try:
                os.remove(path)
            except:
                pass

    # Exibe resultados se os dados foram processados
    if 'structured_data' in locals() and structured_data:
        st.write(show_cv_result(structured_data))
        
        with st.expander("Ver dados estruturados (JSON)"):
            st.json(structured_data)

# Seção de currículos analisados
if os.path.exists(json_file):
    st.subheader("Lista de currículos analisados", divider="gray")
    
    # Botão "Limpar Tudo" centralizado
    col_clear1, col_clear2, col_clear3 = st.columns([1, 2, 1])
    with col_clear2:
        if st.button(
            "🗑️ Limpar Tudo", 
            type="secondary", 
            help="Remove todos os currículos analisados da lista",
            use_container_width=True
        ):
            st.session_state.show_confirm = True
    
    # Modal de confirmação
    if st.session_state.get("show_confirm", False):
        st.warning("⚠️ **Atenção!** Esta ação removerá permanentemente todos os currículos analisados.")
        
        col_confirm1, col_confirm2, col_confirm3 = st.columns([1, 1, 1])
        
        with col_confirm1:
            if st.button("✅ Confirmar", type="primary", use_container_width=True):
                if clear_all_cv(json_file):
                    st.success("✅ Todos os currículos foram removidos com sucesso!")
                    st.session_state.show_confirm = False
                    st.session_state.selected_cv = None  # Limpa currículo selecionado
                    st.rerun()
                else:
                    st.error("❌ Erro ao remover os currículos. Tente novamente.")
        
        with col_confirm3:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state.show_confirm = False
                st.rerun()
    
    # Separador visual
    st.markdown("---")
    
    # Lista de currículos
    try:
        df = display_json_table(json_file)
        
        if not df.empty:
            for i, row in df.iterrows():
                cols = st.columns([1, 3, 1, 5])
                
                with cols[0]:
                    if st.button("Ver detalhes", key=f"btn_{i}"):
                        st.session_state.selected_cv = row.to_dict()
                        st.rerun()
                
                with cols[1]:
                    st.write(f"**Nome:** {row.get('name', '-')}")
                
                with cols[2]:
                    score = row.get('score', 0)
                    if isinstance(score, (int, float)):
                        st.write(f"**Score:** {score:.1f}")
                    else:
                        st.write(f"**Score:** {score}")
                
                with cols[3]:
                    summary = row.get('summary', '-')
                    if len(str(summary)) > 100:
                        summary = str(summary)[:100] + "..."
                    st.write(f"**Resumo:** {summary}")
        else:
            st.info("Nenhum currículo encontrado na base de dados.")
            
    except Exception as e:
        st.error(f"Erro ao carregar currículos: {str(e)}")

# Exibição de currículo selecionado
if st.session_state.selected_cv:
    st.markdown("---")
    st.subheader("Detalhes do Currículo Selecionado")
    st.write(show_cv_result(st.session_state.selected_cv))
    
    with st.expander("Ver dados estruturados (JSON)"):
        st.json(st.session_state.selected_cv)
    
    # Botão para limpar seleção
    if st.button("🔙 Voltar à lista", type="secondary"):
        st.session_state.selected_cv = None
        st.rerun()

# Seção de download e visualização de dados
if os.path.exists(json_file):
    st.markdown("---")
    st.subheader("Exportar Dados", divider="blue")
    
    # Botão de download
    with open(json_file, "r", encoding="utf-8") as f:
        json_data = f.read()
    
    col_download1, col_download2, col_download3 = st.columns([1, 2, 1])
    with col_download2:
        st.download_button(
            label="📥 Baixar arquivo JSON",
            data=json_data,
            file_name=f"curriculos_analisados_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
            help="Baixa todos os currículos analisados em formato JSON"
        )
    
    # Tabela completa de dados
    st.subheader("Tabela Completa de Dados")
    try:
        df = display_json_table(json_file)
        if not df.empty:
            # Configura a exibição da tabela
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "score": st.column_config.NumberColumn(
                        "Score",
                        help="Pontuação do candidato (0.0 a 10.0)",
                        min_value=0.0,
                        max_value=10.0,
                        step=0.1,
                        format="%.1f"
                    ),
                    "name": st.column_config.TextColumn(
                        "Nome",
                        help="Nome completo do candidato",
                        width="medium"
                    ),
                    "area": st.column_config.TextColumn(
                        "Área",
                        help="Área de atuação do candidato",
                        width="small"
                    )
                }
            )
        else:
            st.info("Nenhum dado encontrado para exibição.")
            
    except Exception as e:
        st.error(f"Erro ao exibir tabela: {str(e)}")

# Rodapé com informações
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em; padding: 20px 0;'>
        💼 Sistema de Triagem e Análise de Currículos | Desenvolvido com Streamlit e IA
    </div>
    """, 
    unsafe_allow_html=True
)
