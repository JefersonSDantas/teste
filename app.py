import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Dashboard Cuidado Infantil",
    page_icon="👶",
    layout="wide"
)

# --- FUNÇÕES AUXILIARES ---

@st.cache_data
def load_data(file_path):
    """
    Carrega, combina e limpa os dados de todas as ABAS de um arquivo Excel.
    O nome de cada aba é tratado como o nome da 'Unidade'.
    """
    # Verifica se o arquivo existe
    if not os.path.exists(file_path):
        st.error(f"Arquivo não encontrado em '{file_path}'. Verifique se o nome do arquivo está correto e se ele está na pasta 'data'.")
        return None

    # Nomes de coluna esperados para padronização
    column_names = [
        'Nome', 'DN', 'Data_1_Puericultura', 'Dias_1_Puericultura', 'A',
        'Qtd_Puericultura', 'B', 'Qtd_Peso_Altura', 'C',
        'Data_1_Visita_ACS', 'Dias_1_Visita_ACS', 'Data_2_Visita_ACS',
        'Dias_2_Visita_ACS', 'D', 'E'
    ]

    list_of_dfs = []
    try:
        # Lê todas as abas (planilhas) do arquivo Excel, pulando as 3 primeiras linhas
        all_sheets = pd.read_excel(file_path, sheet_name=None, skiprows=3, header=0)

        if not all_sheets:
            st.warning("O arquivo Excel parece estar vazio ou não contém abas.")
            return None

        # Itera sobre cada aba (que representa uma unidade)
        for unit_name, df in all_sheets.items():
            # Remove colunas totalmente vazias
            df.dropna(axis=1, how='all', inplace=True)

            # Garante que o dataframe tem o número correto de colunas e aplica os nomes
            if len(df.columns) >= len(column_names):
                df = df.iloc[:, :len(column_names)]
                df.columns = column_names
                # Adiciona a coluna 'Unidade' com base no nome da aba
                df['Unidade'] = unit_name.strip()
                list_of_dfs.append(df)
            else:
                st.warning(f"A aba '{unit_name}' foi ignorada porque não possui colunas suficientes.")

    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo Excel '{file_path}'. Erro: {e}")
        return None

    if not list_of_dfs:
        return None

    combined_df = pd.concat(list_of_dfs, ignore_index=True)

    # Limpeza final dos dados
    combined_df.dropna(subset=['Nome', 'DN'], inplace=True)
    combined_df['DN'] = pd.to_datetime(combined_df['DN'], errors='coerce')

    return combined_df

def calculate_score(row):
    """
    Calcula a pontuação para cada criança com base nas boas práticas (A, B, C, D, E).
    Cada boa prática cumprida ('OK') vale 20 pontos.
    """
    score = 0
    indicadores = ['A', 'B', 'C', 'D', 'E']
    for indicador in indicadores:
        if row[indicador] == 'OK':
            score += 20
    return score

def get_classification(score):
    """
    Classifica a pontuação em categorias conforme a Nota Metodológica.
    """
    if 75 < score <= 100:
        return 'Ótimo'
    elif 50 < score <= 75:
        return 'Bom'
    elif 25 < score <= 50:
        return 'Suficiente'
    else:
        return 'Regular'

# --- INTERFACE DO DASHBOARD ---

st.title("👶 Dashboard de Monitoramento - Cuidado Infantil (Indicador C2)")
st.markdown("Este painel visualiza o desempenho das unidades de saúde com base na Nota Metodológica C2.")

# Define o caminho do arquivo Excel
# IMPORTANTE: Se o nome do seu arquivo não for 'monitoramento.xlsx', altere-o aqui.
EXCEL_FILE_PATH = os.path.join('data', 'monitoramento.xlsx')

# Instruções para o usuário
st.info(
    "**Instrução:** Para que o dashboard funcione, crie uma pasta chamada `data` no mesmo "
    "diretório deste script. Dentro da pasta `data`, coloque seu arquivo Excel de monitoramento "
    f"(o sistema está procurando por `{os.path.basename(EXCEL_FILE_PATH)}`).\n\n"
    "**Importante:** Cada aba (planilha) dentro do arquivo Excel deve representar os dados de uma Unidade de Saúde."
)

# Verifica se a pasta 'data' existe
if not os.path.exists('data'):
    st.error("A pasta 'data' não foi encontrada. Por favor, crie-a e adicione o arquivo Excel.")
else:
    # Carrega e processa os dados a partir do arquivo Excel
    df = load_data(EXCEL_FILE_PATH)

    if df is None or df.empty:
        st.error("Nenhum dado válido foi encontrado. Verifique se o arquivo Excel está na pasta 'data' e se as abas estão no formato correto.")
    else:
        df['Pontuação'] = df.apply(calculate_score, axis=1)
        df['Classificação'] = df['Pontuação'].apply(get_classification)

        # --- BARRA LATERAL DE FILTROS ---
        st.sidebar.header("Filtros")
        
        # Filtro por Unidade de Saúde
        all_units = sorted(df['Unidade'].unique())
        selected_units = st.sidebar.multiselect(
            "Selecione a(s) Unidade(s) de Saúde",
            options=all_units,
            default=all_units
        )
        
        # Filtro por Classificação
        all_classifications = ['Ótimo', 'Bom', 'Suficiente', 'Regular']
        selected_classifications = st.sidebar.multiselect(
            "Selecione a(s) Classificação(ões)",
            options=all_classifications,
            default=all_classifications
        )

        # Aplica os filtros
        df_filtered = df[
            df['Unidade'].isin(selected_units) &
            df['Classificação'].isin(selected_classifications)
        ]

        if df_filtered.empty:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
        else:
            # --- SEÇÃO DE MÉTRICAS GERAIS ---
            st.header("Visão Geral")
            col1, col2, col3 = st.columns(3)

            avg_score = df_filtered['Pontuação'].mean()
            
            with col1:
                st.metric(label="Crianças Monitoradas", value=f"{df_filtered.shape[0]:,}")
            with col2:
                st.metric(label="Pontuação Média Geral", value=f"{avg_score:.1f}")
            with col3:
                classification_geral = get_classification(avg_score)
                st.metric(label="Classificação Geral", value=classification_geral)
            
            st.markdown("---")

            # --- SEÇÃO DE GRÁFICOS ---
            
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                # Gráfico 1: Pontuação média por Unidade
                st.subheader("Pontuação Média por Unidade de Saúde")
                df_unit_score = df_filtered.groupby('Unidade')['Pontuação'].mean().sort_values(ascending=False).reset_index()
                
                fig_unit = px.bar(
                    df_unit_score,
                    x='Pontuação',
                    y='Unidade',
                    orientation='h',
                    text=df_unit_score['Pontuação'].apply(lambda x: f'{x:.1f}'),
                    color='Pontuação',
                    color_continuous_scale=px.colors.sequential.Viridis,
                    labels={'Pontuação': 'Pontuação Média', 'Unidade': 'Unidade de Saúde'}
                )
                fig_unit.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_unit, use_container_width=True)

            with col_chart2:
                # Gráfico 2: Conformidade por Boa Prática
                st.subheader("% de Conformidade por Boa Prática")
                indicadores = ['A', 'B', 'C', 'D', 'E']
                compliance_data = []
                for ind in indicadores:
                    ok_count = (df_filtered[ind] == 'OK').sum()
                    total_count = df_filtered[ind].notna().sum()
                    compliance = (ok_count / total_count) * 100 if total_count > 0 else 0
                    compliance_data.append({'Indicador': f'Prática {ind}', 'Conformidade (%)': compliance})
                
                df_compliance = pd.DataFrame(compliance_data)

                fig_compliance = px.bar(
                    df_compliance,
                    x='Indicador',
                    y='Conformidade (%)',
                    text=df_compliance['Conformidade (%)'].apply(lambda x: f'{x:.1f}%'),
                    color='Indicador',
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    labels={'Conformidade (%)': 'Conformidade (%)', 'Indicador': 'Boa Prática'}
                )
                st.plotly_chart(fig_compliance, use_container_width=True)

                # --- SEÇÃO DE TABELA DETALHADA ---
st.markdown("---")
st.header("Análise Detalhada por Criança")

# Seleciona e renomeia colunas para exibição
display_cols = {
    'Nome': 'Nome',
    'DN': 'Data de Nascimento',
    'Unidade': 'Unidade',
    'Pontuação': 'Pontuação',
    'Classificação': 'Classificação',
    'A': 'Prática A',
    'B': 'Prática B',
    'C': 'Prática C',
    'D': 'Prática D',
    'E': 'Prática E'
}
df_display = df_filtered[list(display_cols.keys())].rename(columns=display_cols)
# Formata a data para melhor visualização na tabela
df_display['Data de Nascimento'] = df_display['Data de Nascimento'].dt.strftime('%d/%m/%Y')

# --- FORMATAÇÃO CONDICIONAL (ESTILO EXCEL) ---

# 1. Função para colorir as células das práticas
def style_practices(val):
    """Colore o fundo da célula de verde se for 'OK', vermelho se tiver outro valor, e deixa padrão se estiver vazia."""
    if val == 'OK':
        color = '#d4edda'  # Verde claro
        font_color = '#155724' # Verde escuro
    elif pd.notna(val):
        color = '#f8d7da'  # Vermelho claro
        font_color = '#721c24' # Vermelho escuro
    else:
        color = ''
        font_color = ''
    return f'background-color: {color}; color: {font_color}'

# 2. Lista de colunas onde o estilo será aplicado
practice_columns = ['Prática A', 'Prática B', 'Prática C', 'Prática D', 'Prática E']

# 3. Aplica os estilos ao dataframe e exibe
st.dataframe(
    df_display.style
    # Formata as colunas das práticas
    .applymap(style_practices, subset=practice_columns)
    # Adiciona uma barra de cor na pontuação (do vermelho ao verde)
    .background_gradient(cmap='RdYlGn', subset=['Pontuação'], vmin=0, vmax=100)
    # Formata a pontuação para não ter casas decimais
    .format({'Pontuação': '{:.0f}'}),
    use_container_width=True,
    height=500 # Define uma altura fixa para a tabela com barra de rolagem
)