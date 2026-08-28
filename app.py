import threading
import customtkinter as ctk
from bots.dietas import executar_bot_dietas
from bots.patrimonio import executar_bot_patrimonio

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class CentralAutomacaoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Central de Automações — RPA")
        self.geometry("750x650")
        self.minsize(600, 500)

        # Configurações de acesso ao sistema
        self.URL_SISTEMA = "http://192.168.0.253"
        self.USUARIO = "yurijaciel2@gmail.com"
        self.SENHA = "180725"

        self.criar_widgets()

    def criar_widgets(self):
        # Título
        self.lbl_titulo = ctk.CTkLabel(self, text="Painel de Automações", font=ctk.CTkFont(size=22, weight="bold"))
        self.lbl_titulo.pack(pady=(15, 5))

        # Seletor do Robô
        self.lbl_robo = ctk.CTkLabel(self, text="Selecione o Robô:", font=ctk.CTkFont(size=14))
        self.lbl_robo.pack(anchor="w", padx=25, pady=(5, 0))

        self.combo_robos = ctk.CTkOptionMenu(
            self,
            values=["Cadastro de Patrimônio (TI)", "Cadastro de Dietas (Nutrição)"],
            width=300
        )
        self.combo_robos.pack(anchor="w", padx=25, pady=(0, 10))

        # Caixa de Texto
        self.lbl_dados = ctk.CTkLabel(self, text="Cole os dados para cadastro abaixo:", font=ctk.CTkFont(size=14))
        self.lbl_dados.pack(anchor="w", padx=25, pady=(5, 0))

        self.txt_entrada = ctk.CTkTextbox(self, height=180, font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_entrada.pack(fill="x", padx=25, pady=(0, 15))

        # Botão Iniciar
        self.btn_iniciar = ctk.CTkButton(
            self,
            text="▶ Iniciar Automação",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=40,
            command=self.iniciar_em_segundo_plano
        )
        self.btn_iniciar.pack(fill="x", padx=25, pady=(0, 15))

        # Logs
        self.lbl_log = ctk.CTkLabel(self, text="Logs de Execução:", font=ctk.CTkFont(size=13))
        self.lbl_log.pack(anchor="w", padx=25, pady=(0, 2))

        self.txt_log = ctk.CTkTextbox(self, height=150, font=ctk.CTkFont(family="Consolas", size=11), state="disabled")
        self.txt_log.pack(fill="both", expand=True, padx=25, pady=(0, 20))

    def adicionar_log(self, mensagem):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", f"{mensagem}\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def iniciar_em_segundo_plano(self):
        texto = self.txt_entrada.get("1.0", "end").strip()
        if not texto:
            self.adicionar_log("⚠️ Cole os dados na caixa de texto antes de iniciar.")
            return

        robo_selecionado = self.combo_robos.get()
        self.btn_iniciar.configure(state="disabled", text="⏳ Executando...")

        def tarefa():
            try:
                if robo_selecionado == "Cadastro de Patrimônio (TI)":
                    executar_bot_patrimonio(texto, self.adicionar_log, self.URL_SISTEMA, self.USUARIO, self.SENHA)
                elif robo_selecionado == "Cadastro de Dietas (Nutrição)":
                    executar_bot_dietas(texto, self.adicionar_log, self.URL_SISTEMA + "/nutricao/dietas", self.USUARIO, self.SENHA)
            except Exception as e:
                self.adicionar_log(f"❌ Erro durante a execução: {e}")
            finally:
                self.btn_iniciar.configure(state="normal", text="▶ Iniciar Automação")

        threading.Thread(target=tarefa, daemon=True).start()

if __name__ == "__main__":
    app = CentralAutomacaoApp()
    app.mainloop()