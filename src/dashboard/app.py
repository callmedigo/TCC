import streamlit as st
import os
import glob
from datetime import datetime
from views import bsc, visao_geral, cronograma, proximas_atividades, graficos

st.set_page_config(
    page_title="Dashboard de Projetos",
    page_icon="📊",
    layout="wide",
)

if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 'Lista Mestre'
def navegar_para(pagina):
    st.session_state.pagina_atual = pagina

try:
    arquivos_csv = glob.glob('src/dashboard/data/*.csv')
    if arquivos_csv:
        arquivo_mais_recente = max(arquivos_csv, key=os.path.getmtime)
        tempo_modificacao = os.path.getmtime(arquivo_mais_recente)
        data_atualizacao = datetime.fromtimestamp(tempo_modificacao).strftime("%d/%m %H:%M")
    else:
        data_atualizacao = datetime.now().strftime("%d/%m %H:%M")
except Exception:
    data_atualizacao = datetime.now().strftime("%d/%m %H:%M")

with st.sidebar:
    st.write(f"**Últ. Atualização:**\n{data_atualizacao}") 
    st.divider()
    st.button("Lista Mestre", 
              type="primary" if st.session_state.pagina_atual == "Lista Mestre" else "secondary", 
              use_container_width=True, 
              on_click=navegar_para, args=("Lista Mestre",))
    
    st.button("Gráficos", 
              type="primary" if st.session_state.pagina_atual == "Gráficos" else "secondary", 
              use_container_width=True, 
              on_click=navegar_para, args=("Gráficos",))
    
    st.button("Projetos", 
              type="primary" if st.session_state.pagina_atual == "Projetos" else "secondary", 
              use_container_width=True, 
              on_click=navegar_para, args=("Projetos",))
    
    st.button("Atividades Mensais", 
              type="primary" if st.session_state.pagina_atual == "Atividades Mensais" else "secondary", 
              use_container_width=True, 
              on_click=navegar_para, args=("Atividades Mensais",))
              
    st.button("BSC", 
              type="primary" if st.session_state.pagina_atual == "BSC" else "secondary", 
              use_container_width=True, 
              on_click=navegar_para, args=("BSC",))

if st.session_state.pagina_atual == "Lista Mestre":
    visao_geral.show()
elif st.session_state.pagina_atual == "Gráficos":
    graficos.show()
elif st.session_state.pagina_atual == "Projetos":
    cronograma.show()
elif st.session_state.pagina_atual == "Atividades Mensais":
    proximas_atividades.show()
elif st.session_state.pagina_atual == "BSC":
    bsc.show()