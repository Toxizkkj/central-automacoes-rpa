import re
from playwright.sync_api import sync_playwright

def executar_bot_patrimonio(texto_bruto, log_callback, url, usuario, senha, unidade_selecionada):
    linhas = texto_bruto.strip().splitlines()
    setor_atual = None
    equipamentos = []

    for linha in linhas:
        texto = linha.strip()
        if not texto:
            continue

        if re.search(r"-\s*-\s*-", texto):
            setor_atual = re.split(r"-\s*-\s*-", texto)[0].strip()
            continue

        if "-" in texto and setor_atual:
            partes = [p.strip() for p in texto.split("-")]
            equipamentos.append({
                "setor": setor_atual,
                "nome": partes[0] if len(partes) > 0 else "",
                "codigo": partes[1] if len(partes) > 1 else "",
                "marca": partes[2] if len(partes) > 2 else "",
                "modelo": partes[3] if len(partes) > 3 else ""
            })

    if not equipamentos:
        log_callback("⚠️ Nenhum equipamento válido encontrado no texto.")
        return

    log_callback(f"🚀 Iniciando cadastro de {len(equipamentos)} equipamentos na unidade: [{unidade_selecionada}]...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        log_callback("Efetuando login...")
        page.goto(url)
        page.fill("#email", usuario)
        page.fill("#senha", senha)
        page.click("body > div.login-container > div > form > button")
        page.wait_for_load_state("networkidle")

        # Validação de Login com Sucesso
        try:
            page.wait_for_selector("body > section > div > a.system-link.chamados", timeout=4000)
        except Exception:
            browser.close()
            raise ValueError("Falha no login! Verifique o e-mail e a senha informados e tente novamente.")

        # Fechar pendências se houver
        try:
            btn_pend = page.locator("#modal-pendencias > div > div.portal-actions > button, #modal-pendencias button:has-text('Fechar')")
            if btn_pend.is_visible(timeout=3000):
                log_callback("Fechando modal de pendências...")
                btn_pend.click()
                page.wait_for_timeout(500)
        except Exception:
            pass

        # Acessar Módulo Chamados
        page.click("body > section > div > a.system-link.chamados > h2")
        page.wait_for_load_state("networkidle")

        # Menu Equipamentos
        page.click("#appSidebar > ul > li:nth-child(7) > a > span")
        page.wait_for_load_state("networkidle")

        for idx, item in enumerate(equipamentos, start=1):
            log_callback(f"[{idx}/{len(equipamentos)}] Processando: {item['nome']} (Cod: {item['codigo']}) - Setor: [{item['setor']}]")
            page.click("#btnNovoEq")
            page.wait_for_timeout(500)

            # Verifica se o setor já existe
            setor_existe = page.evaluate("""(setor) => {
                const sel = document.querySelector('#eq_setor');
                if (!sel) return false;
                for (let o of sel.options) {
                    if (o.text.trim().toLowerCase() === setor.trim().toLowerCase()) return true;
                }
                return false;
            }""", item["setor"])

            if not setor_existe:
                log_callback(f"⚙️ Criando novo setor: {item['setor']}")
                page.click("#btnFecharEq")
                page.wait_for_timeout(400)
                page.click("#btnAdicionarSetorEq")
                page.wait_for_timeout(400)
                page.click("#btnNovoSetorEq")
                page.fill("#setorNome", item["setor"])
                page.click("#modalSetor > div.tec-modal-foot > button.btn.btn-success.tec-btn-sm")
                page.wait_for_timeout(600)
                page.click("#modalListaSetores > div.tec-modal-foot > button")
                page.wait_for_timeout(400)
                page.click("#btnNovoEq")
                page.wait_for_timeout(400)

            # Preenchimento dos campos
            page.fill("#eq_codigo", item["codigo"])
            page.fill("#eq_nome", item["nome"])
            if item["marca"]:
                page.fill("#eq_marca", item["marca"])
            if item["modelo"]:
                page.fill("#eq_modelo", item["modelo"])

            # Local / Cliente selecionado dinamicamente
            page.evaluate("""(unidade) => {
                const sel = document.querySelector('#eq_local');
                if (sel) {
                    for (let o of sel.options) {
                        if (o.text.trim().toLowerCase() === unidade.trim().toLowerCase()) {
                            sel.value = o.value;
                            sel.dispatchEvent(new Event('change', { bubbles: true }));
                            sel.dispatchEvent(new Event('input', { bubbles: true }));
                            break;
                        }
                    }
                }
            }""", unidade_selecionada)
            page.wait_for_timeout(300)

            # Setor
            page.evaluate("""(setor) => {
                const sel = document.querySelector('#eq_setor');
                if (sel) {
                    for (let o of sel.options) {
                        if (o.text.trim().toLowerCase() === setor.trim().toLowerCase()) {
                            sel.value = o.value;
                            sel.dispatchEvent(new Event('change', { bubbles: true }));
                            sel.dispatchEvent(new Event('input', { bubbles: true }));
                            break;
                        }
                    }
                }
            }""", item["setor"])
            page.wait_for_timeout(300)

            page.click("#btnGravarEq")
            page.wait_for_timeout(1000)

        log_callback("✅ Todos os equipamentos foram cadastrados com sucesso!")
        browser.close()