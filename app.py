import os
import sys
import threading
import customtkinter as ctk
from PIL import Image, ImageDraw
from bots.dietas import executar_bot_dietas
from bots.patrimonio import executar_bot_patrimonio

# Configuração para localizar o Chromium portátil embutido na pasta
def configurar_caminho_playwright():
    if hasattr(sys, '_MEIPASS'):
        caminho_temp = os.path.join(sys._MEIPASS, "ms-playwright")
        if os.path.exists(caminho_temp):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = caminho_temp
            return
            
    caminho_executavel = os.path.dirname(os.path.abspath(sys.argv[0]))
    caminho_local = os.path.join(caminho_executavel, "ms-playwright")
    if os.path.exists(caminho_local):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = caminho_local

configurar_caminho_playwright()

ctk.set_appearance_mode("Light")

# Paleta de Cores
COR_BRANCO_PURO = "#FFFFFF"        # Fundo geral
COR_CARD_BG = "#FFFFFF"            # Fundo dos cards normais
COR_CARD_TOPO_VERDE = "#06373A"    # Verde Escuro da marca para o cabeçalho
COR_BORDA = "#E2E8F0"              # Borda sutil dos cards (Slate 200)
COR_TEXTO_TITULO = "#0F172A"       # Título escuro
COR_TEXTO_PADRAO = "#334155"       # Texto padrão
COR_INPUT_BG = "#F8FAFC"           # Fundo dos inputs
COR_AZUL_BOTAO = "#0284C7"         # Botão azul corporativo
COR_AZUL_HOVER = "#0369A1"
COR_TEAL_MENU = "#0F766E"

LISTA_UNIDADES = [
    "São Geraldo (Matriz)",
    "Assim Saúde (São Jose)",
    "CAPS III Maria do Socorro ( Rocinha)",
    "Centro Pediátrico da Lagoa",
    "Cliente Teste",
    "Hospital Estadual Tavares de Macedo (HETM)",
    "Hospital Federal Cardoso Fontes",
    "Hospital Federal de Bonsucesso",
    "Hospital Federal de Ipanema",
    "Hospital Municipal Lourenço Jorge",
    "Hospital Municipal Oceânico",
    "Hospital municipal Paulino Werneck",
    "Med Sênior - Campo Grande",
    "Pronto Baby",
    "UERJ"
]

def obter_caminho_recurso(nome_arquivo):
    """Obtém o caminho absoluto para arquivos de assets no Python e no PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        caminho_temp = os.path.join(sys._MEIPASS, nome_arquivo)
        if os.path.exists(caminho_temp):
            return caminho_temp
            
    caminho_diretorio = os.path.dirname(os.path.abspath(sys.argv[0]))
    caminho_local = os.path.join(caminho_diretorio, nome_arquivo)
    if os.path.exists(caminho_local):
        return caminho_local

    return os.path.join(os.path.abspath("."), nome_arquivo)

def arredondar_cantos_imagem(imagem, raio=12):
    """Cria cantos arredondados na imagem com antialiasing."""
    imagem = imagem.convert("RGBA")
    mascara = Image.new("L", imagem.size, 0)
    draw = ImageDraw.Draw(mascara)
    draw.rounded_rectangle((0, 0, imagem.size[0], imagem.size[1]), radius=raio, fill=255)
    
    img_arredondada = Image.new("RGBA", imagem.size, (0, 0, 0, 0))
    img_arredondada.paste(imagem, (0, 0), mask=mascara)
    return img_arredondada

class CentralAutomacaoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Central de Automações — São Geraldo Service")
        self.geometry("820x840")
        self.minsize(700, 700)
        self.configure(fg_color=COR_BRANCO_PURO)

        self.URL_SISTEMA = "http://192.168.0.253"

        self.criar_widgets()

    def criar_widgets(self):
        # 1. Topo com Cabeçalho Verde Escuro
        self.frame_topo = ctk.CTkFrame(
            self, 
            fg_color=COR_CARD_TOPO_VERDE, 
            corner_radius=12
        )
        self.frame_topo.pack(fill="x", padx=25, pady=(15, 10))

        # Carrega a Logo com suporte a caminhos no .exe
        caminho_logo = obter_caminho_recurso("logo.png")
        if os.path.exists(caminho_logo):
            try:
                img_original = Image.open(caminho_logo)
                w, h = img_original.size
                altura_desejada = 48
                largura_proporcional = int(w * (altura_desejada / h))
                
                img_redimensionada = img_original.resize((largura_proporcional, altura_desejada), Image.Resampling.LANCZOS)
                img_com_cantos = arredondar_cantos_imagem(img_redimensionada, raio=10)

                img_logo = ctk.CTkImage(
                    light_image=img_com_cantos,
                    dark_image=img_com_cantos,
                    size=(largura_proporcional, altura_desejada)
                )
                self.lbl_logo = ctk.CTkLabel(self.frame_topo, image=img_logo, text="")
                self.lbl_logo.pack(side="left", padx=16, pady=12)
            except Exception:
                pass

        self.frame_titulos = ctk.CTkFrame(self.frame_topo, fg_color="transparent")
        self.frame_titulos.pack(side="left", fill="y", expand=True, padx=10, pady=12)

        self.lbl_titulo = ctk.CTkLabel(
            self.frame_titulos,
            text="Central de Automações RPA",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#FFFFFF",
            anchor="w"
        )
        self.lbl_titulo.pack(anchor="w")

        self.lbl_subtitulo = ctk.CTkLabel(
            self.frame_titulos,
            text="Módulo de Integração e Cadastro Automatizado",
            font=ctk.CTkFont(size=12),
            text_color="#99F6E4",
            anchor="w"
        )
        self.lbl_subtitulo.pack(anchor="w")

        # 2. Card de Credenciais
        self.frame_login = ctk.CTkFrame(self, fg_color=COR_CARD_BG, border_color=COR_BORDA, border_width=1, corner_radius=12)
        self.frame_login.pack(fill="x", padx=25, pady=(0, 10))

        self.lbl_login_info = ctk.CTkLabel(
            self.frame_login,
            text="Credenciais do Sistema",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COR_TEXTO_TITULO
        )
        self.lbl_login_info.pack(anchor="w", padx=15, pady=(10, 4))

        self.frame_campos_login = ctk.CTkFrame(self.frame_login, fg_color="transparent")
        self.frame_campos_login.pack(fill="x", padx=15, pady=(0, 12))

        self.txt_usuario = ctk.CTkEntry(
            self.frame_campos_login,
            placeholder_text="E-mail de Login",
            fg_color=COR_INPUT_BG,
            border_color=COR_BORDA,
            text_color=COR_TEXTO_PADRAO,
            height=36
        )
        self.txt_usuario.pack(side="left", padx=(0, 10), expand=True, fill="x")

        self.txt_senha = ctk.CTkEntry(
            self.frame_campos_login,
            placeholder_text="Senha",
            show="*",
            fg_color=COR_INPUT_BG,
            border_color=COR_BORDA,
            text_color=COR_TEXTO_PADRAO,
            height=36
        )
        self.txt_senha.pack(side="left", expand=True, fill="x")

        # 3. Card de Configurações do Robô
        self.frame_config = ctk.CTkFrame(self, fg_color=COR_CARD_BG, border_color=COR_BORDA, border_width=1, corner_radius=12)
        self.frame_config.pack(fill="x", padx=25, pady=(0, 10))

        self.frame_selecao = ctk.CTkFrame(self.frame_config, fg_color="transparent")
        self.frame_selecao.pack(fill="x", padx=15, pady=12)

        # Seletor Robô
        self.frame_col_robo = ctk.CTkFrame(self.frame_selecao, fg_color="transparent")
        self.frame_col_robo.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.lbl_robo = ctk.CTkLabel(self.frame_col_robo, text="Módulo / Robô:", font=ctk.CTkFont(size=13, weight="bold"), text_color=COR_TEXTO_TITULO)
        self.lbl_robo.pack(anchor="w", pady=(0, 4))

        self.combo_robos = ctk.CTkOptionMenu(
            self.frame_col_robo,
            values=["Cadastro de Patrimônio (Equipamentos)", "Cadastro de Dietas (Nutrição)"],
            command=self.ao_trocar_robo,
            fg_color=COR_TEAL_MENU,
            button_color="#115E59",
            height=36
        )
        self.combo_robos.pack(fill="x")

        # Seletor Unidade
        self.frame_col_unidade = ctk.CTkFrame(self.frame_selecao, fg_color="transparent")
        self.frame_col_unidade.pack(side="left", expand=True, fill="x")

        self.lbl_unidade = ctk.CTkLabel(self.frame_col_unidade, text="Unidade (Local / Cliente):", font=ctk.CTkFont(size=13, weight="bold"), text_color=COR_TEXTO_TITULO)
        self.lbl_unidade.pack(anchor="w", pady=(0, 4))

        self.combo_unidades = ctk.CTkOptionMenu(
            self.frame_col_unidade,
            values=LISTA_UNIDADES,
            fg_color=COR_TEAL_MENU,
            button_color="#115E59",
            height=36
        )
        self.combo_unidades.pack(fill="x")

        # 4. Campo de Dados
        self.frame_dados = ctk.CTkFrame(self, fg_color=COR_CARD_BG, border_color=COR_BORDA, border_width=1, corner_radius=12)
        self.frame_dados.pack(fill="x", padx=25, pady=(0, 10))

        self.lbl_dados = ctk.CTkLabel(self.frame_dados, text="Dados para Cadastro (Cole a listagem aqui):", font=ctk.CTkFont(size=13, weight="bold"), text_color=COR_TEXTO_TITULO)
        self.lbl_dados.pack(anchor="w", padx=15, pady=(10, 4))

        self.txt_entrada = ctk.CTkTextbox(
            self.frame_dados,
            height=130,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=COR_INPUT_BG,
            border_color=COR_BORDA,
            border_width=1,
            text_color=COR_TEXTO_PADRAO
        )
        self.txt_entrada.pack(fill="x", padx=15, pady=(0, 12))

        # 5. Botão Iniciar
        self.btn_iniciar = ctk.CTkButton(
            self,
            text="▶ Iniciar Cadastro Automático",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#FFFFFF",
            fg_color=COR_AZUL_BOTAO,
            hover_color=COR_AZUL_HOVER,
            height=42,
            corner_radius=8,
            command=self.iniciar_em_segundo_plano
        )
        self.btn_iniciar.pack(fill="x", padx=25, pady=(0, 10))

        # 6. Painel de Logs
        self.frame_logs = ctk.CTkFrame(self, fg_color=COR_CARD_BG, border_color=COR_BORDA, border_width=1, corner_radius=12)
        self.frame_logs.pack(fill="both", expand=True, padx=25, pady=(0, 15))

        self.lbl_log = ctk.CTkLabel(self.frame_logs, text="Progresso da Execução:", font=ctk.CTkFont(size=13, weight="bold"), text_color=COR_TEXTO_TITULO)
        self.lbl_log.pack(anchor="w", padx=15, pady=(10, 4))

        self.txt_log = ctk.CTkTextbox(
            self.frame_logs,
            height=110,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COR_INPUT_BG,
            border_color=COR_BORDA,
            border_width=1,
            text_color="#0369A1",
            state="disabled"
        )
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=(0, 12))

    def ao_trocar_robo(self, escolha):
        if escolha == "Cadastro de Dietas (Nutrição)":
            self.combo_unidades.configure(state="disabled")
        else:
            self.combo_unidades.configure(state="normal")

    def adicionar_log(self, mensagem):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", f"{mensagem}\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def iniciar_em_segundo_plano(self):
        usuario = self.txt_usuario.get().strip()
        senha = self.txt_senha.get().strip()
        texto = self.txt_entrada.get("1.0", "end").strip()
        unidade = self.combo_unidades.get()
        robo_selecionado = self.combo_robos.get()

        if not usuario or not senha:
            self.adicionar_log("- Informe o e-mail e a senha de acesso antes de iniciar.")
            return

        if not texto:
            self.adicionar_log("- Cole os dados na caixa de texto antes de iniciar.")
            return

        self.btn_iniciar.configure(state="disabled", text="- Executando...")

        def tarefa():
            try:
                if robo_selecionado == "Cadastro de Patrimônio (Equipamentos)":
                    executar_bot_patrimonio(texto, self.adicionar_log, self.URL_SISTEMA, usuario, senha, unidade)
                elif robo_selecionado == "Cadastro de Dietas (Nutrição)":
                    executar_bot_dietas(texto, self.adicionar_log, self.URL_SISTEMA, usuario, senha)
            except ValueError as ve:
                self.adicionar_log(f"- {ve}")
            except Exception as e:
                self.adicionar_log(f"- Erro durante a execução: {e}")
            finally:
                self.btn_iniciar.configure(state="normal", text="▶ Iniciar Cadastro Automático")

        threading.Thread(target=tarefa, daemon=True).start()

if __name__ == "__main__":
    app = CentralAutomacaoApp()
    app.mainloop()