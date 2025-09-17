import streamlit as st
import uuid
from utils import *
from dotenv import load_dotenv
import os
import tempfile
from datetime import datetime

# Carrega variáveis de ambiente
load_dotenv()

# Configuração da página
st.set_page_config(
    page_title="Sistema de Triagem de Currículos - Calçados Beira Rio", 
    page_icon="👔", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS customizado para melhor aparência
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79 0%, #2e5984 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .main-header h1 {
        color: white !important;
        margin: 0;
        text-align: center;
    }
    
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f4e79;
        margin: 0.5rem 0;
    }
    
    .cv-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: #fafafa;
    }
    
    .score-excellent { color: #28a745; font-weight: bold; }
    .score-good { color: #ffc107; font-weight: bold; }
    .score-average { color: #fd7e14; font-weight: bold; }
    .score-poor { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Header principal
st.markdown("""
<div class="main-header">
    <h1>👔 Sistema de Triagem e Análise de Currículos</h1>
    <p style="color: white; text-align: center; margin: 0;">Calçados Beira Rio S.A. | Powered by AI</p>
</div>
""", unsafe_allow_html=True)

# Verificação da chave API
if not os.getenv("GROQ_API_KEY"):
    st.error("❌ **Configuração necessária:** GROQ_API_KEY não encontrada!")
    st.info("""
    **Para configurar:**
    1. Acesse as configurações do Streamlit Cloud
    2. Vá em **Settings** → **Secrets** 
    3. Adicione: `GROQ_API_KEY = "sua_chave_api_aqui"`
    4. Reinicie a aplicação
    """)
    st.stop()

# Configurações da aplicação
CONFIG = {
    "model": "deepseek-r1-distill-llama-70b",
    "temperature": 0.7,
    "json_file": "curriculos_beira_rio.json",
    "job_csv": "vaga_atual.csv",
    "max_file_size": 10 * 1024 * 1024  # 10MB
}

# Cache do modelo para otimizar performance
@st.cache_resource
def initialize_llm():
    """Inicializa o modelo LLM com cache"""
    return load_llm(CONFIG["model"], CONFIG["temperature"])

# Inicialização do modelo
try:
    with st.spinner("🔄 Inicializando sistema de IA..."):
        llm = initialize_llm()
    st.success("✅ Sistema inicializado com sucesso!")
except Exception as e:
    st.error(f"❌ Erro na inicialização: {str(e)}")
    st.stop()

# Definição da vaga (adaptada para Calçados Beira Rio)
vaga_beira_rio = {
    'title': "Desenvolvedor(a) Full Stack Sênior - Calçados Beira Rio",
    'description': """
    A Calçados Beira Rio, líder no mercado calçadista brasileiro, busca um(a) Desenvolvedor(a) Full Stack 
    Sênior para integrar nosso time de tecnologia. O profissional será responsável por desenvolver e manter 
    sistemas críticos que suportam nossas operações em mais de 97 países, seguindo nossos rigorosos padrões 
    de desenvolvimento e qualidade.
    """,
    'details': """
**RESPONSABILIDADES:**
• Desenvolver e manter aplicações web seguindo padrões internos (Padronizacao_Desenvolvimento.md)
• Implementar soluções em ambiente Oracle Database com PL/SQL
• Seguir nomenclatura padrão: FCT_ (funções), PRC_ (procedures), PCK_ (packages)
• Criar e manter Forms e Reports seguindo templates corporativos
• Participar de code reviews e documentação técnica
• Colaborar em projetos de integração com sistemas ERP
• Desenvolver dashboards e relatórios para gestão

**REQUISITOS OBRIGATÓRIOS:**
• 5+ anos de experiência em desenvolvimento Full Stack
• Domínio avançado em PL/SQL e Oracle Database
• Experiência com Oracle Forms e Reports
• Conhecimento sólido em JavaScript, HTML5, CSS3
• Experiência com versionamento Git
• Capacidade de seguir padrões rigorosos de desenvolvimento
• Inglês técnico para leitura

**REQUISITOS DESEJÁVEIS:**
• Experiência em sistemas ERP (especialmente calçadista)
• Conhecimento em Power BI ou ferramentas BI
• Certificações Oracle
• Experiência com metodologias ágeis
• Conhecimento em AWS ou Google Cloud Platform
• Graduação em áreas correlatas

**DIFERENCIAIS:**
• Experiência no setor calçadista ou varejo
• Projetos de integração complexos
• Liderança de equipes técnicas
• Contribuições em projetos open source
• Conhecimento em automação de testes

**OFERECEMOS:**
• Salário compatível com o mercado + benefícios
• Plano de saúde e odontológico
• Vale-refeição e vale-transporte
• Participação nos lucros e resultados
• Oportunidades de crescimento em empresa global
• Ambiente de trabalho inovador e sustentável
    """
}

# Schema de dados estruturados para análise
schema_cv = """
{
  "name": "Nome completo do candidato",
  "area": "Área principal de atuação (Desenvolvimento, TI, Outros)",
  "summary": "Resumo objetivo do perfil profissional",
  "skills": ["lista de competências técnicas relevantes"],
  "education": "Resumo da formação acadêmica mais relevante",
  "experience_years": "Número estimado de anos de experiência",
  "interview_questions": ["3 a 5 perguntas específicas para entrevista"],
  "strengths": ["pontos fortes alinhados com a vaga"],
  "areas_for_development": ["lacunas ou pontos de atenção"],
  "important_considerations": ["observações que merecem verificação"],
  "final_recommendations": "Avaliação final e próximos passos sugeridos",
  "score": 0.0
}
"""

# Campos obrigatórios para validação
required_fields = [
    "name", "area", "summary", "skills", "education", "experience_years",
    "interview_questions", "strengths", "areas_for_development", 
    "important_considerations", "final_recommendations", "score"
]

# Instruções detalhadas para pontuação
scoring_instructions = """
CRITÉRIOS DE PONTUAÇÃO (0.0 a 10.0):

1. **EXPERIÊNCIA TÉCNICA (Peso: 40%)**
   - Anos de experiência em desenvolvimento
   - Experiência com Oracle/PL-SQL (fundamental)
   - Conhecimento em Forms/Reports
   - Projetos similares ao ambiente corporativo

2. **HABILIDADES TÉCNICAS (Peso: 25%)**
   - Linguagens de programação relevantes
   - Banco de dados Oracle
   - Ferramentas de desenvolvimento web
   - Conhecimento em metodologias ágeis

3. **FORMAÇÃO E CERTIFICAÇÕES (Peso: 15%)**
   - Graduação em áreas correlatas
   - Certificações técnicas (especialmente Oracle)
   - Cursos de especialização relevantes

4. **ALINHAMENTO CULTURAL (Peso: 10%)**
   - Experiência em ambientes corporativos
   - Capacidade de seguir padrões rigorosos
   - Trabalho em equipe e comunicação

5. **DIFERENCIAIS (Peso: 10%)**
   - Experiência no setor calçadista/varejo
   - Liderança técnica
   - Projetos de integração complexos
   - Inglês técnico

**ESCALA DE PONTUAÇÃO:**
- 9.0-10.0: Candidato excepcional, supera expectativas
- 7.0-8.9: Candidato muito qualificado, alta aderência
- 5.0-6.9: Candidato qualificado, boa aderência
- 3.0-4.9: Candidato com potencial, necessita desenvolvimento
- 0.0-2.9: Candidato inadequado para a posição

SEJA RIGOROSO E JUSTO. Note 10.0 apenas para candidatos extraordinários.
"""

# Template do prompt para análise
prompt_template = ChatPromptTemplate.from_template("""
Você é um especialista em Recursos Humanos da Calçados Beira Rio S.A., empresa líder no setor calçadista brasileiro.

Sua tarefa é analisar o currículo a seguir e extrair informações estruturadas conforme o schema JSON especificado.

IMPORTANTE:
- Retorne APENAS o JSON estruturado, sem explicações adicionais
- Use exatamente as chaves especificadas no schema
- Seja preciso e detalhado na análise
- Considere o contexto da empresa e da vaga específica

SCHEMA ESPERADO:
{schema}

INSTRUÇÕES PARA PONTUAÇÃO:
{prompt_score}

DETALHES DA VAGA:
{job}

CURRÍCULO PARA ANÁLISE:
{cv}

Retorne apenas o JSON estruturado:
""")

# Estados da sessão
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())
if "selected_cv" not in st.session_state:
    st.session_state.selected_cv = None
if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []

# Salva informações da vaga
save_job_to_csv(vaga_beira_rio, CONFIG["job_csv"])
job_details = load_job(CONFIG["job_csv"])

# Layout principal em duas colunas
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📄 Análise de Currículo")
    
    # Informações da vaga
    with st.expander("💼 Detalhes da Vaga", expanded=False):
        st.markdown(f"**{vaga_beira_rio['title']}**")
        st.write(vaga_beira_rio['description'])
        
        st.markdown("**Principais Requisitos:**")
        st.markdown("""
        • 5+ anos em desenvolvimento Full Stack
        • Oracle Database e PL/SQL avançado
        • Oracle Forms e Reports
        • JavaScript, HTML5, CSS3
        • Git e metodologias ágeis
        """)

with col_right:
    st.subheader("📤 Upload de Currículo")
    
    # Upload de arquivo
    uploaded_file = st.file_uploader(
        "Selecione um arquivo PDF", 
        type=["pdf"], 
        key=st.session_state.uploader_key,
        help="Tamanho máximo: 10MB | Apenas arquivos PDF"
    )
    
    if st.button("🔄 Limpar Upload"):
        st.session_state.uploader_key = str(uuid.uuid4())
        st.rerun()

# Processamento do arquivo enviado
if uploaded_file is not None:
    file_size = len(uploaded_file.read())
    uploaded_file.seek(0)  # Reset do ponteiro do arquivo
    
    if file_size > CONFIG["max_file_size"]:
        st.error(f"❌ Arquivo muito grande ({file_size/1024/1024:.1f}MB). Máximo permitido: 10MB")
    else:
        try:
            # Cria arquivo temporário seguro
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.read())
                temp_path = tmp_file.name
            
            # Interface de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("🔄 Extraindo texto do documento...")
            progress_bar.progress(25)
            
            # Processa o CV
            with st.spinner("🤖 Analisando currículo com IA... Isso pode levar 1-2 minutos."):
                status_text.text("🤖 Enviando para análise de IA...")
                progress_bar.progress(50)
                
                output, response = process_cv(
                    schema_cv, 
                    job_details, 
                    prompt_template, 
                    scoring_instructions, 
                    llm, 
                    temp_path
                )
                
                progress_bar.progress(75)
                status_text.text("📊 Processando resultados...")
                
                if output and response:
                    # Extrai dados estruturados
                    cv_data = parse_res_llm(response, required_fields)
                    
                    if validate_cv_data(cv_data):
                        # Salva os dados
                        if save_json_cv(cv_data, CONFIG["json_file"], "name"):
                            progress_bar.progress(100)
                            status_text.text("✅ Análise concluída com sucesso!")
                            
                            # Atualiza interface
                            st.session_state.uploader_key = str(uuid.uuid4())
                            st.session_state.analysis_history.append({
                                "timestamp": datetime.now(),
                                "filename": uploaded_file.name,
                                "candidate": cv_data.get("name", "N/A"),
                                "score": cv_data.get("score", 0)
                            })
                            
                            # Exibe resultados
                            st.success("🎉 Currículo analisado e salvo com sucesso!")
                            
                            # Métricas rápidas
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("👤 Candidato", cv_data.get("name", "N/A"))
                            with col2:
                                score = float(cv_data.get("score", 0))
                                st.metric("📊 Pontuação", f"{score}/10")
                            with col3:
                                st.metric("💼 Área", cv_data.get("area", "N/A"))
                            
                            st.markdown("---")
                            st.markdown(show_cv_result(cv_data))
                            
                            # Dados estruturados (expandível)
                            with st.expander("🔍 Ver Dados Estruturados (JSON)"):
                                st.json(cv_data)
                                
                        else:
                            st.error("❌ Erro ao salvar os dados do currículo.")
                    else:
                        st.error("❌ Dados extraídos são inválidos. Tente novamente.")
                else:
                    st.error("❌ Falha na análise. Verifique se o arquivo é um PDF válido.")
            
            # Remove arquivo temporário
            try:
                os.unlink(temp_path)
            except:
                pass
                
            # Limpa indicadores de progresso
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            st.error(f"❌ Erro no processamento: {str(e)}")
            if "rate limit" in str(e).lower():
                st.info("⏳ Limite de requisições atingido. Aguarde alguns minutos e tente novamente.")
            elif "timeout" in str(e).lower():
                st.info("⏳ Timeout na análise. O documento pode ser muito complexo.")

# Seção de currículos analisados
st.markdown("---")
st.header("📋 Currículos Analisados")

if os.path.exists(CONFIG["json_file"]):
    df = display_json_table(CONFIG["json_file"])
    
    if not df.empty:
        # Estatísticas rápidas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Analisados", len(df))
        
        with col2:
            avg_score = df['score'].mean() if 'score' in df.columns else 0
            st.metric("📈 Pontuação Média", f"{avg_score:.1f}")
        
        with col3:
            excellent_count = len(df[df['score'] >= 8]) if 'score' in df.columns else 0
            st.metric("🌟 Candidatos Excelentes", excellent_count)
        
        with col4:
            qualified_count = len(df[df['score'] >= 6]) if 'score' in df.columns else 0
            st.metric("✅ Candidatos Qualificados", qualified_count)
        
        st.markdown("---")
        
        # Filtros
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            min_score = st.slider("Pontuação mínima", 0.0, 10.0, 0.0, 0.1)
        
        with col_filter2:
            if 'area' in df.columns:
                areas = df['area'].unique().tolist()
                selected_area = st.selectbox("Filtrar por área", ["Todas"] + areas)
            else:
                selected_area = "Todas"
        
        # Aplica filtros
        filtered_df = df.copy()
        if 'score' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['score'] >= min_score]
        if selected_area != "Todas" and 'area' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['area'] == selected_area]
        
        # Ordena por pontuação
        if 'score' in filtered_df.columns:
            filtered_df = filtered_df.sort_values('score', ascending=False)
        
        # Lista de candidatos
        st.subheader(f"👥 Lista de Candidatos ({len(filtered_df)} encontrados)")
        
        for idx, row in filtered_df.iterrows():
            with st.container():
                cols = st.columns([1, 3, 1, 1, 3, 1])
                
                with cols[0]:
                    if st.button("👁️", key=f"view_{idx}", help="Ver detalhes"):
                        st.session_state.selected_cv = row.to_dict()
                
                with cols[1]:
                    st.markdown(f"**{row.get('name', 'N/A')}**")
                
                with cols[2]:
                    score = row.get('score', 0)
                    if score >= 8:
                        st.markdown(f'<span class="score-excellent">🟢 {score}</span>', unsafe_allow_html=True)
                    elif score >= 6:
                        st.markdown(f'<span class="score-good">🟡 {score}</span>', unsafe_allow_html=True)
                    elif score >= 4:
                        st.markdown(f'<span class="score-average">🟠 {score}</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="score-poor">🔴 {score}</span>', unsafe_allow_html=True)
                
                with cols[3]:
                    st.write(f"*{row.get('area', 'N/A')}*")
                
                with cols[4]:
                    experience = row.get('experience_years', 'N/A')
                    summary = str(row.get('summary', ''))
                    preview = summary[:80] + "..." if len(summary) > 80 else summary
                    st.write(f"{experience} anos | {preview}")
                
                with cols[5]:
                    timestamp = row.get('analyzed_at', 'N/A')
                    if timestamp != 'N/A':
                        try:
                            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                            st.write(dt.strftime("%d/%m %H:%M"))
                        except:
                            st.write("N/A")
                    else:
                        st.write("N/A")
                
                st.markdown("---")
        
        # Exibe detalhes do CV selecionado
        if st.session_state.selected_cv:
            st.markdown("## 🔍 Detalhes do Candidato Selecionado")
            st.markdown(show_cv_result(st.session_state.selected_cv))
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("❌ Fechar Detalhes"):
                    st.session_state.selected_cv = None
                    st.rerun()
            
            with col2:
                with st.expander("📄 Dados Estruturados"):
                    st.json(st.session_state.selected_cv)
        
        # Opções de download
        st.markdown("---")
        st.subheader("📥 Downloads")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Download JSON
            with open(CONFIG["json_file"], "r", encoding="utf-8") as f:
                json_data = f.read()
            
            st.download_button(
                label="📄 Baixar dados completos (JSON)",
                data=json_data,
                file_name=f"curriculos_beira_rio_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
        
        with col2:
            # Download CSV
            csv_data = filtered_df.to_csv(index=False, encoding='utf-8')
            st.download_button(
                label="📊 Baixar lista filtrada (CSV)",
                data=csv_data,
                file_name=f"lista_candidatos_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        # Tabela completa (expandível)
        with st.expander("📊 Visualizar Tabela Completa"):
            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True
            )
    
    else:
        st.info("📝 Nenhum currículo foi analisado ainda. Faça o upload do primeiro arquivo!")

else:
    st.info("📂 Nenhum dado encontrado. Comece analisando o primeiro currículo!")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.8em; margin-top: 2rem;">
    <p>💼 Sistema de Triagem de Currículos | Calçados Beira Rio S.A.</p>
    <p>Desenvolvido com Streamlit + IA | Versão 1.0 | 2024</p>
</div>
""", unsafe_allow_html=True)

# Limpeza periódica (executar silenciosamente)
try:
    clean_old_files()
except:
    pass