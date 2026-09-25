import re
import time
from playwright.sync_api import sync_playwright

def selecionar_dropdown_js(page, seletor_css, texto_opcao):
    if not texto_opcao:
        return False
    
    return page.evaluate(r"""({seletor, textoOpcao}) => {
        const norm = (s) => s ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, " ").trim().toLowerCase() : "";
        
        let sel = document.querySelector(seletor);
        if (!sel) return false;
        
        const termoAlvo = norm(textoOpcao);
        let encontrou = false;
        
        for (let o of sel.options) {
            const txt = norm(o.text);
            if (txt === termoAlvo) {
                sel.value = o.value;
                encontrou = true;
                break;
            }
        }
        
        if (encontrou) {
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            sel.dispatchEvent(new Event('input', { bubbles: true }));
            if (window.jQuery && window.jQuery(sel).length) {
                window.jQuery(sel).trigger('change');
            }
            return true;
        }
        return false;
    }""", {"seletor": seletor_css, "textoOpcao": str(texto_opcao)})

def executar_bot_dietas(texto_bruto, log_callback, url, usuario, senha, categoria_selecionada="Básica / Oral"):
    texto_bruto = texto_bruto.strip()
    modo_apagar_massa = False
    
    if texto_bruto.lower().startswith("apagar dietas"):
        modo_apagar_massa = True

    linhas = texto_bruto.splitlines()
    grupo_atual = "Sem grupo" 
    dietas = []

    if not modo_apagar_massa:
        for linha in linhas:
            texto = linha.strip()
            if not texto:
                continue

            if texto.endswith(":") or (":" in texto and " " not in texto.split(":")[-1]):
                grupo_atual = texto.replace(":", "").strip()
                continue

            if not any(k in texto.upper() for k in ["NOME DA DIETA", "ENFERMARIAS:", "DATA:"]):
                dietas.append({
                    "nome": texto,
                    "grupo": grupo_atual
                })

        if not dietas:
            log_callback("- Nenhuma dieta válida encontrada no texto.")
            return

        log_callback(f"- Iniciando cadastro de {len(dietas)} dietas com a categoria [{categoria_selecionada}]...")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False, channel="chrome")
        except Exception:
            try:
                browser = p.chromium.launch(headless=False, channel="msedge")
            except Exception:
                browser = p.chromium.launch(headless=False)

        page = browser.new_page()
        
        dialog_confirmacao = {"ocorreu": False, "mensagem": ""}
        def tratar_dialog(dialog):
            dialog_confirmacao["ocorreu"] = True
            dialog_confirmacao["mensagem"] = dialog.message
            dialog.accept() 
            
        page.on("dialog", tratar_dialog)

        log_callback("Efetuando login no sistema...")
        page.goto(url)
        page.fill('input[type="email"], input[name="email"], #email', usuario)
        page.fill('input[type="password"], input[name="password"], #senha', senha)
        page.click("button:has-text('Entrar'), button[type='submit'], body > div.login-container > div > form > button")
        page.wait_for_load_state("networkidle")

        try:
            page.wait_for_selector("text='Escolha o sistema para continuar', text='Sistema Nutrição Hospitalar', a.nutricao", timeout=4000)
            card_nutricao = page.locator("text='Sistema Nutrição Hospitalar', a:has-text('Acessar'):near(:text('Nutrição Hospitalar'))").first
            if card_nutricao.is_visible():
                card_nutricao.click()
                page.wait_for_load_state("networkidle")
        except Exception:
            pass 

        try:
            page.wait_for_selector("body > section > div > a.system-link.nutricao, a.nutricao", timeout=4000)
            link_nutricao = page.locator("body > section > div > a.system-link.nutricao > span, a.nutricao").first
            if link_nutricao.is_visible():
                link_nutricao.click()
                page.wait_for_load_state("networkidle")
        except Exception:
            pass

        try:
            page.click("#appSidebar > ul > li:nth-child(5) > a, a:has-text('Cadastro')", timeout=3000)
            page.wait_for_timeout(500)
            # Seletor estrito passado por você, sem fallbacks para evitar clicar em Grupos de Dietas
            page.click("#cadastro-submenu > li:nth-child(7) > a")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
        except Exception:
            log_callback("- Erro: Não foi possivel localizar o menu Cadastro > Dietas.")
            browser.close()
            return
            
        # ---------------------------------------------------------
        # FLUXO DE EXCLUSAO EM MASSA
        # ---------------------------------------------------------
        if modo_apagar_massa:
            log_callback("Iniciando MODO DE EXCLUSÃO DE DIETAS EM MASSA...")
            apagadas = 0
            
            page.wait_for_timeout(1500)
            
            while True:
                try:
                    primeira_linha = page.locator('#tabelaDietasBody tr:nth-child(1), table tbody tr:nth-child(1)').first
                    primeira_linha.wait_for(state="visible", timeout=3000)
                except Exception:
                    break
                    
                btn_excluir = primeira_linha.locator('td.dieta-acoes > button:nth-child(2), button:has-text("Excluir")').first
                
                try:
                    btn_excluir.click(timeout=2000)
                    page.wait_for_timeout(500)
                    
                    btn_ok_modal = page.locator('.swal2-confirm, #modalConfirmBtn, button:has-text("OK")').first
                    if btn_ok_modal.is_visible(timeout=1000):
                        btn_ok_modal.click()
                        
                    page.wait_for_timeout(1500)
                    apagadas += 1
                    
                    if apagadas % 5 == 0:
                        log_callback(f"Progresso: {apagadas} dietas excluídas...")
                except Exception as e:
                    log_callback(f"Aviso: Erro ao tentar excluir linha, interrompendo loop. Erro: {e}")
                    break
                    
            log_callback(f"Exclusão em massa finalizada. Total apagado: {apagadas}.")
            browser.close()
            return

        # ---------------------------------------------------------
        # FLUXO DE CADASTRO NORMAL
        # ---------------------------------------------------------
        cadastradas = 0
        
        for idx, item in enumerate(dietas, start=1):
            nome_dieta = item["nome"].upper()
            grupo_dieta = item["grupo"]
            
            log_callback(f"[{idx}/{len(dietas)}] Cadastrando: {nome_dieta} | Grupo: {grupo_dieta}")
            
            try:
                page.click("body > main > div > div.toolbar > button, button:has-text('Nova Dieta'), #btnNovaDieta", timeout=3000)
            except Exception:
                page.click(".dieta-cadastro .toolbar button")
            
            page.wait_for_timeout(600)
            
            page.fill("input[name*='nome'], #f-dieta-nome", nome_dieta)
            page.wait_for_timeout(200)

            if grupo_dieta and grupo_dieta != "Sem grupo":
                selecionar_dropdown_js(page, "select[name*='grupo'], #f-dieta-grupo", grupo_dieta)
            
            selecionar_dropdown_js(page, "select[name*='categoria'], #f-dieta-categoria", categoria_selecionada)
            page.wait_for_timeout(300)

            page.click("button:has-text('Salvar'), #modalConfirmBtn, .btn-success")
            page.wait_for_timeout(1200)
            
            cadastradas += 1

        log_callback(f"- Concluído: {cadastradas} dietas foram cadastradas com sucesso!")
        browser.close()