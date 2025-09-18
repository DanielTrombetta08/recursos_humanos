import os
from docling.document_converter import DocumentConverter
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
import json
import pandas as pd
import csv
import streamlit as st

def load_llm(id_model, temperature):
  llm = ChatGroq(
      model=id_model,
      temperature=temperature,
      max_tokens=None,
      timeout=None,
      max_retries=2,
  )
  return llm


def format_res(res, return_thinking=False):
  res = res.strip()

  if return_thinking:
    res = res.replace("<think>", "[pensando...] ")
    res = res.replace("</think>", "\n---\n")

  else:
    if "</think>" in res:
      res = res.split("</think>")[-1].strip()

  return res


def parse_doc(file_path):
  converter = DocumentConverter()
  result = converter.convert(file_path)
  content = result.document.export_to_markdown()
  return content


def parse_res_llm(response_text: str, required_fields: list) -> dict:
    try:
        # Remove a parte do raciocínio (<think>...</think>)
        if "</think>" in response_text:
            response_text = response_text.split("</think>")[-1].strip()

        # Localiza o JSON e faz o parsing
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx == -1 or end_idx == 0:
            raise json.JSONDecodeError("Nenhum JSON encontrado na resposta", response_text, 0)

        json_str = response_text[start_idx:end_idx]
        info_cv = json.loads(json_str)

        for field in required_fields:
            if field not in info_cv:
                info_cv[field] = []

        return info_cv

    except json.JSONDecodeError:
        #Erro ao interpretar a resposta do modelo
        return


def save_json_cv(new_data, path_json, key_name="name"):
    # Carrega o JSON existente, se houver
    if os.path.exists(path_json):
        with open(path_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    if isinstance(data, dict):
        data = [data]

    # Verifica se já existe um currículo com o mesmo nome
    candidates = [entry.get(key_name) for entry in data]
    if new_data.get(key_name) in candidates:
        st.warning(f"Currículo '{new_data.get(key_name)}' já registrado. Ignorando.")
        return

    # Adiciona e salva
    data.append(new_data)
    with open(path_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json_cv(path_json):
    with open(path_json, "r", encoding="utf-8") as f:
        return json.load(f)


def show_cv_result(result: dict):
    md = f"### 📄 Análise e Resumo do Currículo\n"
    if "name" in result:
        md += f"- **Nome:** {result['name']}\n"
    if "area" in result:
        md += f"- **Área de Atuação:** {result['area']}\n"
    if "skills" in result:
        md += f"- **Competências:** {', '.join(result['skills'])}\n"
    if "summary" in result:
        md += f"- **Resumo do Perfil:** {result['summary']}\n"
    if "interview_questions" in result:
        md += f"- **Perguntas sugeridas:**\n"
        md += "\n".join([f"  - {q}" for q in result["interview_questions"]]) + "\n"
    if "strengths" in result:
        md += f"- **Pontos fortes (ou Alinhamentos):**\n"
        md += "\n".join([f"  - {s}" for s in result["strengths"]]) + "\n"
    if "areas_for_development" in result:
        md += f"- **Pontos a desenvolver (ou Desalinhamentos):**\n"
        md += "\n".join([f"  - {a}" for a in result["areas_for_development"]]) + "\n"
    if "important_considerations" in result:
        md += f"- **Pontos de atenção:**\n"
        md += "\n".join([f"  - {i}" for i in result["important_considerations"]]) + "\n"
    if "final_recommendations" in result:
        md += f"- **Conclusão e recomendações:** {result['final_recommendations']}\n"
    return md


def save_job_to_csv(data, filename):
    headers = ['title', 'description', 'details']
    file_exists = os.path.exists(filename)

    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter=';')
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)


def load_job(csv_path):
  try:
    df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
    job = df.iloc[-1]
    prompt_text = f"""
    **Vaga para {job['title']}**

    **Descrição da Vaga:**
    {job['description']}

    **Detalhes Completos:**
    {job['details']}
    """

    return prompt_text.strip()

  except FileNotFoundError:
    return "Erro: Arquivo de vagas não encontrado"

def process_cv(schema, job_details, prompt_template, prompt_score, llm, file_path):

  if file_path:
    if not os.path.exists(file_path):
      raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

  content = parse_doc(file_path)

  chain = prompt_template | llm
  output = chain.invoke({"schema": schema, "cv": content, "job": job_details, "prompt_score": prompt_score})

  res = format_res(output.content)

  return output, res


def display_json_table(path_json):
  with open(path_json, "r", encoding="utf-8") as f:
    data = json.load(f)

  df = pd.DataFrame(data)
  return df
