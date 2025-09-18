import os
import streamlit as st
import uuid
import time
from utils import *
from dotenv import load_dotenv
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

st.set_page_config(page_title="Triagem e Análise de Currículos", page_icon="📄", layout="wide")

id_model = "deepseek-r1-distill-llama-70b"
temperature = 0.7
json_file = 'curriculos.json'
path_job_csv = "vagas.csv"

llm = load_llm(id_model, temperature)

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

# ✅ SOLUÇÃO 3: Estados aprimorados para reset automático
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())
if "processing_complete" not in st.session_state:
    st.session_state.processing_complete = False
if "last_processed_file" not in st.session_state:
    st.session_state.last_processed_file = None
if "selected_cv" not in st.session_state:
    st.session_state.selected_cv = None
if "structured_data" not in st.session_state:
    st.session_state.structured_data = None

# Salva descrição da vaga em um .csv
save_job_to_csv(job, path_job_csv)
job_details = load_job(path_job_csv)

# ✅ Layout aprimorado com botão de reset
col1, col2 = st.columns(2)

with col1:
    st.header("Triagem e Análise de Currículos")
    st.markdown("#### Vaga: {}".format(job["title"]))

with col2:
    # Botão de reset manual
    col_upload, col_reset = st.columns([4, 1])
    
    with col_reset:
        if st.button("🔄", help="Resetar upload"):
            st.session_state.uploader_key = str(uuid.uuid4())
            st.session_state.processing_complete = False
            st.session_state.last_processed_file = None
            st.session_state.structured_data = None
            st.rerun()
    
    with col_upload:
        uploaded_file = st.file_uploader(
            "Envie um currículo em PDF", 
            type=["pdf"], 
            key=st.session_state.uploader_key
        )

# ✅ Processamento com reset automático
if uploaded_file is not None:
    # Verificar se é um novo arquivo ou reprocessamento
    if st.session_state.last_processed_file != uploaded_file.name:
        
        with st.spinner("Analisando o currículo..."):
            path = uploaded_file.name
            with open(path, "wb") as f:
                f.write(uploaded_file.read())
            
            try:
                output, res = process_cv(schema, job_details, prompt_template, prompt_score, llm, path)
                structured_data = parse_res_llm(res, fields)
                save_json_cv(structured_data, path_json=json_file, key_name="name")
                
                # Marcar como processado
                st.session_state.last_processed_file = uploaded_file.name
                st.session_state.processing_complete = True
                st.session_state.structured_data = structured_data
                
                # Limpar arquivo temporário
                if os.path.exists(path):
                    os.remove(path)
                
                st.success("✅ Currículo analisado com sucesso!")
                
                # Aguardar um pouco antes do reset automático
                time.sleep(0.5)
                
                # Reset automático do uploader
                st.session_state.uploader_key = str(uuid.uuid4())
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Erro ao processar: {str(e)}")
                # Reset em caso de erro
                st.session_state.uploader_key = str(uuid.uuid4())
                st.session_state.processing_complete = False

# ✅ Mostrar resultados se disponíveis
if st.session_state.processing_complete and st.session_state.structured_data:
    
    # Botão para analisar outro currículo
    if st.button("📤 Analisar Outro Currículo", type="primary"):
        st.session_state.uploader_key = str(uuid.uuid4())
        st.session_state.processing_complete = False
        st.session_state.last_processed_file = None
        st.session_state.structured_data = None
        st.rerun()
    
    st.write(show_cv_result(st.session_state.structured_data))
    
    with st.expander("Ver dados estruturados (JSON)"):
        st.json(st.session_state.structured_data)

# Lista de currículos analisados
if os.path.exists(json_file):
    st.subheader("Lista de currículos analisados", divider="gray")
    df = display_json_table(json_file)
    
    for i, row in df.iterrows():
        cols = st.columns([1, 3, 1, 5])
        with cols[0]:
            if st.button("Ver detalhes", key=f"btn_{i}"):
                st.session_state.selected_cv = row.to_dict()
        with cols[1]:
            st.write(f"**Nome:** {row.get('name', '-')}")
        with cols[2]:
            st.write(f"**Score:** {row.get('score', '-')}")
        with cols[3]:
            st.write(f"**Resumo:** {row.get('summary', '-')}")

# Mostrar detalhes do currículo selecionado
if st.session_state.selected_cv:
    st.markdown("-----")
    st.write(show_cv_result(st.session_state.selected_cv))
    with st.expander("Ver dados estruturados (JSON)"):
        st.json(st.session_state.selected_cv)

# Download e visualização dos dados
if os.path.exists(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        json_data = f.read()
    
    st.download_button(
        label="📥 Baixar arquivo .json",
        data=json_data,
        file_name=json_file,
        mime="application/json"
    )
    
    df = display_json_table(json_file)
    st.dataframe(df)
