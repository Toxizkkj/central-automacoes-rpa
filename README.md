# Central de Automacoes RPA

Aplicacao desktop desenvolvida em Python para automacao de rotinas operacionais (RPA), integrando o cadastro em lote de equipamentos e dietas hospitalares em sistema web interno. A ferramenta reduz o tempo de digitacao manual, padroniza as entradas e minimiza falhas humanas no preenchimento de formularios.

---

## Funcionalidades

- **Interface Grafica Integrada:** Painel desktop intuitivo construido com CustomTkinter, oferecendo suporte a temas visuais modernos e controle unificado das rotinas.
- **Modulo de Patrimonio (Equipamentos):**
  - Parsing automatico de texto para extracao de setor, nome, codigo, marca e modelo.
  - Verificacao dinamica e criacao de novos setores quando nao encontrados previamente no sistema.
  - Vinculacao direta de equipamentos a unidade/cliente selecionada.
- **Modulo de Dietas (Nutricao):**
  - Filtragem de cabecalhos de planilhas/textos brutos.
  - Cadastro em lote com preenchimento padronizado de categorias e grupos de atendimento.
- **Execucao Assincrona:** Rotinas de automacao executadas em threads dedicadas, mantendo a interface grafica responsiva durante todo o processamento.
- **Log em Tempo Real:** Terminal embutido na aplicacao para acompanhamento passo a passo do fluxo e deteccao imediata de falhas.
- **Compatibilidade Portavel:** Suporte a empacotamento com PyInstaller via deteccao dinamica de caminhos (`_MEIPASS`) e uso de navegadores Chromium/Edge nativos do sistema operacional.

---

## Tecnologias Utilizadas

- **Linguagem:** Python 3
- **Interface Grafica:** CustomTkinter, Pillow (PIL)
- **Automacao Web (RPA):** Playwright
- **Distribuicao:** PyInstaller (suporte a executavel standalone)

---

## Estrutura do Projeto

```text
central-automacoes-rpa/
│
├── app.py                     # Ponto de entrada e interface grafica (CustomTkinter)
├── logo.png                   # Identidade visual da aplicacao
├── bots/
│   ├── __init__.py
│   ├── dietas.py              # Automacao de cadastro de dietas
│   └── patrimonio.py          # Automacao de cadastro de patrimonio/equipamentos
│
├── requirements.txt           # Dependencias do projeto
└── README.md                  # Documentacao do repositorio
