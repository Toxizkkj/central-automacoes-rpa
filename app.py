import threading
import customtkinter as ctk
from bots.dietas import executar_bot_dietas
from bots.patrimonio import executar_bot_patrimonio

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

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

class CentralAutomacaoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Central de Automações — RPA")
        self.geometry("780x750")
        self.minsize(680, 650)

        self.URL_SISTEMA = "http://192.168.0.253"

        self.criar_widgets()

    def criar_widgets(self):
        # Título
        self.lbl_titulo = ctk.CTkLabel(self, text="Painel de Automações", font=ctk.CTkFont(size=22, weight="bold"))
        self.lbl_titulo.pack(pady=(12, 10))

        # Quadro de Credenciais de Acesso
        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(fill="x", padx=25, pady=(0, 10))

        self.lbl_login_info = ctk.CTkLabel(self.frame_login, text="Credenciais de Acesso ao Sistema:", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_login_info.pack(anchor="w", padx=15, pady=(8, 4))

        self.frame_campos_login = ctk.CTkFrame(self.frame_login, fg_color="transparent")
        self.frame_campos_login.pack(fill="x", padx=15, pady=(0, 10))

        self.txt_usuario = ctk.CTkEntry(self.frame_campos_login, placeholder_text="E-mail de Login", width=320)
        self.txt_usuario.pack(side="left", padx=(0, 10), expand=True, fill="x")

        self.txt_senha = ctk.CTkEntry(self.frame_campos_login, placeholder_text="Senha", show="*", width=320)
        self.txt_senha.pack(side="left", expand=True, fill="x")

        # Quadro de Seleção de Robô e Unidade
        self.frame_selecao = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_selecao.pack(fill="x", padx=25, pady=(0, 5))

        # Seletor do Robô
        self.frame_col_robo = ctk.CTkFrame(self.frame_selecao, fg_color="transparent")
        self.frame_col_robo.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.lbl_robo = ctk.CTkLabel(self.frame_col_robo, text="Selecione o Robô:", font=ctk.CTkFont(size=13))
        self.lbl_robo.pack(anchor="w", pady=(0, 2))

        self.combo_robos = ctk.CTkOptionMenu(
            self.frame_col_robo,
            values=["Cadastro de Patrimônio (TI)", "Cadastro de Dietas (Nutrição)"],
            command=self.ao_trocar_robo
        )
        self.combo_robos.pack(fill="x")

        # Seletor da Unidade (Local / Cliente)
        self.frame_col_unidade = ctk.CTkFrame(self.frame_selecao, fg_color="transparent")
        self.frame_col_unidade.pack(side="left", expand=True, fill="x")

        self.lbl_unidade = ctk.CTkLabel(self.frame_col_unidade, text="Unidade (Local / Cliente):", font=ctk.CTkFont(size=13))
        self.lbl_unidade.pack(anchor="w", pady=(0, 2))

        self.combo_unidades = ctk.CTkOptionMenu(
            self.frame_col_unidade,
            values=LISTA_UNIDADES
        )
        self.combo_unidades.pack(fill="x")

        # Caixa de Texto para Inserção de Dados
        self.lbl_dados = ctk.CTkLabel(self, text="Cole os dados para cadastro abaixo:", font=ctk.CTkFont(size=13))
        self.lbl_dados.pack(anchor="w", padx=25, pady=(10, 2))

        self.txt_entrada = ctk.CTkTextbox(self, height=140, font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_entrada.pack(fill="x", padx=25, pady=(0, 10))

        # Botão Iniciar
        self.btn_iniciar = ctk.CTkButton(
            self,
            text="▶ Iniciar Automação",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=38,
            command=self.iniciar_em_segundo_plano
        )
        self.btn_iniciar.pack(fill="x", padx=25, pady=(0, 10))

        # Logs
        self.lbl_log = ctk.CTkLabel(self, text="Logs de Execução:", font=ctk.CTkFont(size=13))
        self.lbl_log.pack(anchor="w", padx=25, pady=(0, 2))

        self.txt_log = ctk.CTkTextbox(self, height=140, font=ctk.CTkFont(family="Consolas", size=11), state="disabled")
        self.txt_log.pack(fill="both", expand=True, padx=25, pady=(0, 15))

    def ao_trocar_robo(self, escolha):
        """Desativa a seleção de unidade caso o bot não precise dela (ex: Nutrição)."""
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
            self.adicionar_log("❌ Informe o e-mail e a senha de acesso antes de iniciar.")
            return

        if not texto:
            self.adicionar_log("⚠️ Cole os dados na caixa de texto antes de iniciar.")
            return

        self.btn_iniciar.configure(state="disabled", text="⏳ Executando...")

        def tarefa():
            try:
                if robo_selecionado == "Cadastro de Patrimônio (TI)":
                    executar_bot_patrimonio(texto, self.adicionar_log, self.URL_SISTEMA, usuario, senha, unidade)
                elif robo_selecionado == "Cadastro de Dietas (Nutrição)":
                    executar_bot_dietas(texto, self.adicionar_log, self.URL_SISTEMA, usuario, senha)
            except ValueError as ve:
                self.adicionar_log(f"⚠️ {ve}")
            except Exception as e:
                self.adicionar_log(f"❌ Erro durante a execução: {e}")
            finally:
                self.btn_iniciar.configure(state="normal", text="▶ Iniciar Automação")

        threading.Thread(target=tarefa, daemon=True).start()

if __name__ == "__main__":
    app = CentralAutomacaoApp()
    app.mainloop()