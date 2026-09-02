from playwright.sync_api import sync_playwright

def executar_bot_dietas(texto_bruto, log_callback, url, usuario, senha):
    linhas = texto_bruto.strip().splitlines()
    dietas = [l.strip().upper() for l in linhas if l.strip() and not any(k in l.upper() for k in ["NOME DA DIETA", "ENFERMARIAS:", "DATA:"])]

    if not dietas:
        log_callback("- Nenhuma dieta válida encontrada no texto.")
        return

    log_callback(f"- Iniciando cadastro de {len(dietas)} dietas...")

    with sync_playwright() as p:
        # Tenta abrir o Chrome nativo; se não houver, abre o Edge nativo do Windows
        try:
            browser = p.chromium.launch(headless=False, channel="chrome")
        except Exception:
            try:
                browser = p.chromium.launch(headless=False, channel="msedge")
            except Exception:
                browser = p.chromium.launch(headless=False)

        page = browser.new_page()

        log_callback("Efetuando login no sistema...")
        page.goto(url)
        page.fill("#email", usuario)
        page.fill("#senha", senha)
        page.click("body > div.login-container > div > form > button")
        page.wait_for_load_state("networkidle")

        # Validação de Login com Sucesso
        try:
            page.wait_for_selector("body > section > div > a.system-link.nutricao", timeout=4000)
        except Exception:
            browser.close()
            raise ValueError("Falha no login! Verifique o e-mail e a senha informados e tente novamente.")

        # Acessa Módulo de Nutrição
        page.click("body > section > div > a.system-link.nutricao")
        page.wait_for_load_state("networkidle")

        # Menu Cadastro > Dietas
        page.click("#appSidebar > ul > li:nth-child(5) > a > span")
        page.click("#cadastro-submenu > li:nth-child(5) > a")
        page.wait_for_load_state("networkidle")

        for idx, nome_dieta in enumerate(dietas, start=1):
            log_callback(f"[{idx}/{len(dietas)}] Cadastrando: {nome_dieta}")
            page.click("body > main > div > div.toolbar > button")
            page.wait_for_timeout(400)

            page.fill("#f-dieta-nome", nome_dieta)

            try:
                page.select_option("#f-dieta-grupo", label="DIETAS ORAIS")
            except Exception:
                page.select_option("#f-dieta-grupo", value="DIETAS ORAIS")

            try:
                page.select_option("#f-dieta-categoria", label="Básica / Oral")
            except Exception:
                page.select_option("#f-dieta-categoria", value="Básica / Oral")

            page.click("button:has-text('Salvar')")
            page.wait_for_timeout(1000)

        log_callback("- Todas as dietas foram cadastradas com sucesso!")
        browser.close()