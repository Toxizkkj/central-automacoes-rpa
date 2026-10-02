import os
import pdfplumber
import time
import re
import unicodedata
from playwright.sync_api import sync_playwright

def normalizar_texto(texto):
    if not texto: return ""
    texto_sem_acento = ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', texto_sem_acento.lower())

def extrair_dados_pdf(pdf_path, log_callback):
    cardapio_geral = {}
    with pdfplumber.open(pdf_path) as pdf:
        for num_pagina, page in enumerate(pdf.pages, start=1):
            tabelas = page.extract_tables()
            for tabela in tabelas:
                if not tabela or len(tabela) < 2: continue
                
                header_idx = -1
                dietas_na_tabela = []

                for r_idx, row in enumerate(tabela):
                    row_clean = [str(c).replace('\n', ' ').strip().upper() for c in row if c]
                    
                    if len(row_clean) >= 3 and any("REFEI" in c for c in row_clean):
                        header_idx = r_idx
                        for c_idx, cabecalho in enumerate(row):
                            if not cabecalho: continue
                            
                            c_upper = str(cabecalho).replace('\n', ' ').strip().upper()
                            if c_upper and c_upper not in ["DIA", "REFEIÇÃO", "REFEICAO"]:
                                c_upper = re.sub(r'(?i).*IMPRESSÃO DE CARDÁPIOS\s*', '', c_upper).strip()
                                c_upper = re.sub(r'(?i).*WWW\.TELNETINFO\.COM\.BR\s*', '', c_upper).strip()
                                
                                if c_upper:
                                    dietas_na_tabela.append((c_idx, c_upper))
                        break

                if header_idx == -1 or not dietas_na_tabela:
                    continue 

                dia_atual = "1"
                for linha in tabela[header_idx + 1:]:
                    if not linha or not any(linha): continue
                    
                    raw_dia = str(linha[0]).strip() if linha[0] else ""
                    if raw_dia and raw_dia.isdigit():
                        dia_atual = raw_dia
                    
                    refeicao = str(linha[1]).replace('\n', ' ').strip() if len(linha) > 1 and linha[1] else ""
                    if not refeicao or "REFEI" in refeicao.upper(): continue
                    
                    for col_idx, nome_dieta in dietas_na_tabela:
                        if col_idx < len(linha):
                            conteudo_celula = str(linha[col_idx]).strip()
                            if conteudo_celula and conteudo_celula != "None":
                                if nome_dieta not in cardapio_geral:
                                    cardapio_geral[nome_dieta] = {}
                                if dia_atual not in cardapio_geral[nome_dieta]:
                                    cardapio_geral[nome_dieta][dia_atual] = {}
                                
                                linhas_brutas = [item.strip() for item in conteudo_celula.split('\n') if item.strip()]
                                itens_crus = []
                                
                                for txt in linhas_brutas:
                                    if not itens_crus:
                                        itens_crus.append(txt)
                                    elif txt[0].islower():
                                        itens_crus[-1] += f" {txt}"
                                    else:
                                        itens_crus.append(txt)
                                
                                cardapio_geral[nome_dieta][dia_atual][refeicao] = {
                                    "itens": itens_crus[:10]
                                }
                                
    log_callback(f"- Extração concluída: {len(cardapio_geral)} dietas identificadas no PDF.")
    return cardapio_geral

def selecionar_dropdown_js(page, seletor_css, texto_opcao):
    if not texto_opcao: return False
    return page.evaluate(r"""({seletor, textoOpcao}) => {
        const norm = (s) => s ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, " ").trim().toLowerCase() : "";
        let sel = document.querySelector(seletor);
        if (!sel) return false;
        const termoAlvo = norm(textoOpcao);
        for (let o of sel.options) {
            if (norm(o.text) === termoAlvo) {
                sel.value = o.value;
                sel.dispatchEvent(new Event('change', { bubbles: true }));
                sel.dispatchEvent(new Event('input', { bubbles: true }));
                if (window.jQuery && window.jQuery(sel).length) window.jQuery(sel).trigger('change');
                return true;
            }
        }
        return false;
    }""", {"seletor": seletor_css, "textoOpcao": str(texto_opcao)})

def preencher_autocomplete_com_cadastro(page, seletor_input, seletor_btn_mais, valor_texto):
    if not valor_texto: return
    
    page.fill(seletor_input, "")
    page.wait_for_timeout(50)
    page.fill(seletor_input, valor_texto)
    page.wait_for_timeout(400)  
    
    msg_nenhum = page.locator("text=/Nenhum produto/i").first.is_visible()
    
    js_caca_item = r"""(textoBuscado) => {
        const norm = (s) => s ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, " ").trim().toLowerCase() : "";
        const target = norm(textoBuscado);
        
        const elementos = document.querySelectorAll('li, a, div, span, td');
        for (let i = elementos.length - 1; i >= 0; i--) {
            const el = elementos[i];
            if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                if (['BODY', 'HTML', 'MAIN', 'FORM', 'SECTION', 'TR', 'TBODY', 'TABLE'].includes(el.tagName)) continue;
                
                if (norm(el.innerText || el.textContent) === target) {
                    el.scrollIntoView({ block: 'nearest' });
                    el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                    el.click();
                    el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                    return true;
                }
            }
        }
        return false;
    }"""

    encontrou_exato = False
    
    if not msg_nenhum:
        encontrou_exato = page.evaluate(js_caca_item, valor_texto)
        page.wait_for_timeout(150)
        page.evaluate("document.body.click()") 
        page.wait_for_timeout(100)

    precisa_cadastrar = msg_nenhum or not encontrou_exato
    
    if precisa_cadastrar:
        page.locator(seletor_btn_mais).click(timeout=3000)
        page.wait_for_timeout(300) 
        
        page.locator("#itemExtraNome").fill(valor_texto)
        page.wait_for_timeout(200)
        page.locator("#itemExtraOverlay > div > div.item-extra-footer > button.btn.btn-primary.btn-sm").click()
        page.wait_for_timeout(600) 
        
        # 1. Trata o popup de sucesso "OK" se o sistema jogar na tela
        try:
            btn_ok_extra = page.locator('.swal2-confirm, button:has-text("OK")').first
            if btn_ok_extra.is_visible(timeout=500):
                btn_ok_extra.click()
                page.wait_for_timeout(300)
        except: pass
        
        # 2. Clica orgânicamente no "X" ou aperta "ESC" para sair da tela de cadastro de item
        try:
            if page.locator("#itemExtraOverlay").is_visible():
                btn_fechar_x = page.locator("#itemExtraOverlay .close, #itemExtraOverlay button.close, #itemExtraOverlay button:has-text('×')").first
                if btn_fechar_x.is_visible(timeout=500):
                    btn_fechar_x.click()
                else:
                    page.keyboard.press("Escape")
        except:
            page.keyboard.press("Escape")
            
        page.wait_for_timeout(300)
        
        page.fill(seletor_input, valor_texto)
        page.wait_for_timeout(400) 
        
        page.evaluate(js_caca_item, valor_texto)
        page.wait_for_timeout(150)
        
        valor_pos_cadastro = page.locator(seletor_input).input_value()
        if normalizar_texto(valor_pos_cadastro) != normalizar_texto(valor_texto):
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(50)
            page.keyboard.press("Enter")
            page.evaluate("document.body.click()")
            page.wait_for_timeout(100)

def executar_bot_cardapios(texto_bruto, pdf_path, log_callback, url, usuario, senha, categoria_selecionada="Básica / Oral"):
    texto_bruto = texto_bruto.strip()
    modo_apagar_cardapios = texto_bruto.lower().startswith("apagar card")
    
    grupo_dieta_selecionado = "Sem grupo"
    dietas_ignoradas = []
    
    for linha in texto_bruto.splitlines():
        texto = linha.strip()
        if texto.endswith(":") or (":" in texto and " " not in texto.split(":")[-1]):
            grupo_dieta_selecionado = texto.replace(":", "").strip()
        elif texto.endswith("- - -") and not texto.lower().startswith("apagar") and not texto.lower().startswith("editar"):
            nome_ignorado = texto.replace("- - -", "").strip()
            dietas_ignoradas.append(normalizar_texto(nome_ignorado))
            log_callback(f"- Configurado para ignorar a dieta: {nome_ignorado}")
    
    dados_cardapio = {}
    if not modo_apagar_cardapios:
        if not pdf_path:
            raise ValueError("PDF não fornecido. Anexe o arquivo antes de iniciar.")
        log_callback("Analisando e extraindo dados do PDF... Isso pode levar alguns segundos.")
        try:
            dados_cardapio = extrair_dados_pdf(pdf_path, log_callback)
        except Exception as e:
            raise ValueError(f"Falha ao ler o PDF. Erro: {e}")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False, channel="chrome")
        except Exception:
            browser = p.chromium.launch(headless=False)

        page = browser.new_page()
        dialog_confirmacao = {"ocorreu": False, "mensagem": ""}
        def tratar_dialog(dialog):
            dialog_confirmacao["ocorreu"] = True
            dialog.accept() 
        page.on("dialog", tratar_dialog)

        log_callback("Efetuando login no sistema...")
        page.goto(url)
        page.fill('input[type="email"], input[name="email"], #email', usuario)
        page.fill('input[type="password"], input[name="password"], #senha', senha)
        page.click("button:has-text('Entrar'), button[type='submit']")
        page.wait_for_load_state("networkidle")

        try:
            btn_pend = page.locator("#modal-pendencias > div > div.portal-actions > button, button:has-text('Fechar')")
            if btn_pend.is_visible(timeout=3000):
                btn_pend.click()
                page.wait_for_timeout(300)
        except Exception:
            pass

        try:
            page.wait_for_selector("body > section > div > a.system-link.nutricao", timeout=4000)
            page.click("body > section > div > a.system-link.nutricao")
            page.wait_for_load_state("networkidle")
        except Exception:
            pass 

        try:
            page.click("#appSidebar > ul > li:nth-child(5) > a", timeout=4000) 
            page.wait_for_timeout(300)
        except Exception:
            log_callback("- Erro de navegação. Não achou menu Cadastro.")
            browser.close()
            return

        if modo_apagar_cardapios:
            page.click("#cadastro-submenu > li:nth-child(9) > a > span", timeout=3000) 
            page.wait_for_load_state("networkidle")
            log_callback("Iniciando MODO DE EXCLUSÃO DE CARDÁPIOS EM MASSA...")
            apagadas = 0
            page.wait_for_timeout(1000)
            
            while True:
                try:
                    primeira_linha = page.locator('#tabelaCardapiosBody tr:nth-child(1), table tbody tr:nth-child(1)').first
                    primeira_linha.wait_for(state="visible", timeout=3000)
                except Exception:
                    break
                
                btn_excluir = primeira_linha.locator('button:has-text("Excluir"), button.btn-danger').first
                try:
                    btn_excluir.click(timeout=2000)
                    page.wait_for_timeout(300)
                    btn_ok_modal = page.locator('.swal2-confirm, #modalConfirmBtn, button:has-text("OK")').first
                    if btn_ok_modal.is_visible(timeout=1000): btn_ok_modal.click()
                    page.wait_for_timeout(1000)
                    apagadas += 1
                    if apagadas % 5 == 0: log_callback(f"Progresso: {apagadas} cardápios excluídos...")
                except Exception as e:
                    break
            log_callback(f"Exclusão em massa finalizada. Total apagado: {apagadas}.")
            browser.close()
            return

        log_callback("FASE 1: Verificando se as dietas do PDF existem no sistema...")
        try:
            page.click("#cadastro-submenu > li:nth-child(7) > a", timeout=3000) 
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)
            
            for dieta_nome in dados_cardapio.keys():
                if normalizar_texto(dieta_nome) in dietas_ignoradas:
                    continue
                    
                page.fill("input[placeholder*='Buscar dieta']", "")
                page.wait_for_timeout(100)
                page.fill("input[placeholder*='Buscar dieta']", dieta_nome)
                page.wait_for_timeout(500)
                
                tem_dieta = page.locator("td.dieta-acoes > button, button:has-text('Editar')").first.is_visible()
                
                if not tem_dieta:
                    log_callback(f"Dieta [{dieta_nome}] não encontrada. Auto-cadastrando...")
                    page.click("button:has-text('Nova Dieta'), #btnNovaDieta, .toolbar button")
                    page.wait_for_timeout(300)
                    
                    page.fill("input[name*='nome'], #f-dieta-nome", dieta_nome)
                    page.wait_for_timeout(100)
                    
                    if grupo_dieta_selecionado and grupo_dieta_selecionado != "Sem grupo":
                        selecionar_dropdown_js(page, "select[name*='grupo'], #f-dieta-grupo", grupo_dieta_selecionado)
                        page.wait_for_timeout(150)
                    
                    selecionar_dropdown_js(page, "select[name*='categoria'], #f-dieta-categoria", categoria_selecionada)
                    page.wait_for_timeout(150)
                    
                    page.click("button:has-text('Salvar'), #modalConfirmBtn, .btn-success")
                    page.wait_for_timeout(500)
                    
                    try:
                        btn_ok = page.locator('.swal2-confirm, button:has-text("OK")').first
                        if btn_ok.is_visible(timeout=500): btn_ok.click()
                    except: pass
                    
                    page.wait_for_timeout(300)
        except Exception as e:
            log_callback(f"Aviso na checagem de dietas: {e}")

        page.evaluate("() => { document.querySelectorAll('.modal-overlay, .modal-backdrop, #modalOverlay').forEach(el => el.style.display = 'none'); }")
        page.wait_for_timeout(300)

        log_callback("FASE 2: Iniciando cadastro dos Cardápios...")
        page.click("#cadastro-submenu > li:nth-child(9) > a > span", timeout=3000) 
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
            
        seletores_tabs = {
            "Desjejum": "#abasHorario > button.tab.active, #abasHorario > button:nth-child(1)",
            "Colação": "#abasHorario > button:nth-child(2)", "Almoço": "#abasHorario > button:nth-child(3)",
            "Merenda": "#abasHorario > button:nth-child(4)", "Jantar": "#abasHorario > button:nth-child(5)",
            "Ceia": "#abasHorario > button:nth-child(6)"
        }

        inputs_grandes = [
            "#g-acompanhamento", "#g-prato_base", "#g-proteina_opcional", "#g-guarnicao", "#g-docinho_salada",
            "#g-sobremesa", "#g-fruta", "#g-suco", "#g-vitamina_suco", "#g-outros"
        ]
        botoes_grandes = [
            "#painel-grandes > div > div.col-left > div:nth-child(1) > div > div.campo-input-mais > button",
            "#painel-grandes > div > div.col-left > div:nth-child(2) > div > div.campo-input-mais > button",
            "#painel-grandes > div > div.col-left > div:nth-child(3) > div > div.campo-input-mais > button",
            "#painel-grandes > div > div.col-left > div:nth-child(4) > div > div.campo-input-mais > button",
            "#painel-grandes > div > div.col-left > div:nth-child(5) > div > div.campo-input-mais > button",
            "#painel-grandes > div > div.col-right > div:nth-child(1) > div > div.campo-input-mais > button",
            "#painel-grandes > div > div.col-right > div:nth-child(2) > div > div.campo-input-mais > button",
            "#painel-grandes > div > div.col-right > div:nth-child(3) > div > div.campo-input-mais > button",
            "#painel-grandes > div > div.col-right > div:nth-child(4) > div > div.campo-input-mais > button",
            "#painel-grandes > div > div.col-right > div:nth-child(5) > div > div.campo-input-mais > button"
        ]

        inputs_pequenas = [
            "#p-bebida", "#p-prato1", "#p-prato2", "#p-prato3", "#p-prato4",
            "#p-prato5", "#p-prato6", "#p-prato7", "#p-sobremesa"
        ]
        botoes_pequenas = [
            "#painel-pequenas > div > div:nth-child(1) > div:nth-child(1) > div > div.campo-input-mais > button",
            "#painel-pequenas > div > div:nth-child(1) > div:nth-child(2) > div > div.campo-input-mais > button",
            "#painel-pequenas > div > div:nth-child(1) > div:nth-child(3) > div > div.campo-input-mais > button",
            "#painel-pequenas > div > div:nth-child(1) > div:nth-child(4) > div > div.campo-input-mais > button",
            "#painel-pequenas > div > div:nth-child(1) > div:nth-child(5) > div > div.campo-input-mais > button",
            "#painel-pequenas > div > div:nth-child(2) > div:nth-child(1) > div > div.campo-input-mais > button",
            "#painel-pequenas > div > div:nth-child(2) > div:nth-child(2) > div > div.campo-input-mais > button",
            "#painel-pequenas > div > div:nth-child(2) > div:nth-child(3) > div > div.campo-input-mais > button",
            "#painel-pequenas > div > div:nth-child(2) > div:nth-child(4) > div > div.campo-input-mais > button"
        ]

        for dieta_nome, dados_dias in dados_cardapio.items():
            if normalizar_texto(dieta_nome) in dietas_ignoradas:
                log_callback(f" > Dieta [{dieta_nome}] ignorada pelo comando '- - -'.")
                continue
                
            log_callback(f"Lançando Cardápio: [{dieta_nome}]")
            page.fill("#buscaDieta", "")
            page.wait_for_timeout(100)
            page.fill("#buscaDieta", dieta_nome)
            page.wait_for_timeout(600) 
            
            js_clica_dieta_exata = """(dietaAlvo) => {
                const rows = document.querySelectorAll('#tabelaCardapiosBody tr');
                for (let row of rows) {
                    if (!row.cells || row.cells.length === 0) continue;
                    const nomeLinha = row.cells[0].innerText.trim().toUpperCase();
                    
                    if (nomeLinha === dietaAlvo.toUpperCase()) {
                        const btnMaca = row.cells[1]?.querySelector('button');
                        if (btnMaca) { btnMaca.click(); return true; }
                        
                        const botoes = row.querySelectorAll('button');
                        for (let b of botoes) {
                            if (b.innerText.trim().includes('Editar')) {
                                b.click(); return true;
                            }
                        }
                    }
                }
                return false;
            }"""
            
            clicou_correto = page.evaluate(js_clica_dieta_exata, dieta_nome)
            
            if not clicou_correto:
                log_callback(f"Aviso: Não encontrou maçã ou botão editar para a dieta exata [{dieta_nome}]. Pulando.")
                continue
            
            try:
                page.wait_for_selector("#cardapioModalOverlay", state="visible", timeout=4000)
            except Exception:
                log_callback(f"Aviso: Modal do cardápio não abriu para [{dieta_nome}].")
                continue
            
            for dia in range(1, 32):
                str_dia = str(dia)
                if str_dia not in dados_dias:
                    continue

                log_callback(f" > Dieta [{dieta_nome}] | Processando Dia: {str_dia}")
                
                valor_atual = page.locator("#f-dia-mes").input_value()
                if valor_atual != str_dia:
                    page.locator("#f-dia-mes").click()
                    page.fill("#f-dia-mes", str_dia)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(250)
                    
                    while True:
                        valor_rechecagem = page.locator("#f-dia-mes").input_value()
                        if valor_rechecagem == str_dia:
                            break
                        try:
                            v_int = int(valor_rechecagem)
                        except ValueError:
                            break
                            
                        page.locator("#f-dia-mes").click()
                        if v_int < dia:
                            page.keyboard.press("ArrowUp")
                        else:
                            page.keyboard.press("ArrowDown")
                        page.wait_for_timeout(150)
                
                refeicoes_dia = dados_dias[str_dia]
                for nome_refeicao, abas_selector in seletores_tabs.items():
                    key_busca = next((k for k in refeicoes_dia.keys() if k.upper() == nome_refeicao.upper()), None)
                    if not key_busca: continue
                    
                    try:
                        page.locator(abas_selector).first.click(timeout=2000)
                        page.wait_for_timeout(200) 
                    except Exception: continue 
                    
                    is_refeicao_grande = nome_refeicao.upper() in ["ALMOÇO", "JANTAR"]
                    lista_itens = refeicoes_dia[key_busca].get("itens", [])
                    
                    if is_refeicao_grande:
                        seletores_in = inputs_grandes
                        seletores_btn = botoes_grandes
                    else:
                        seletores_in = inputs_pequenas
                        seletores_btn = botoes_pequenas
                    
                    for idx, texto_item in enumerate(lista_itens):
                        if idx >= len(seletores_in): break
                        
                        seletor_in = seletores_in[idx]
                        seletor_btn = seletores_btn[idx]
                        
                        preencher_autocomplete_com_cadastro(page, seletor_in, seletor_btn, texto_item)
                        
                    try:
                        page.locator("#cardapioModalOverlay > div > div.cardapio-modal-body > div > div.cardapio-toolbar > button.btn.btn-primary.btn-sm, button:has-text('Salvar')").first.click(timeout=3000)
                        page.wait_for_timeout(400) 
                        
                        try:
                            btn_ok_salvar = page.locator('.swal2-confirm, button:has-text("OK")').first
                            if btn_ok_salvar.is_visible(timeout=500):
                                btn_ok_salvar.click()
                                page.wait_for_timeout(150)
                        except: pass
                    except Exception as e:
                        log_callback(f"Erro ao salvar a aba {nome_refeicao}: {e}")
                        
            log_callback(f"Cardápio da Dieta [{dieta_nome}] finalizado.")
            
            try:
                btn_fechar_modal = page.locator("#cardapioModalOverlay > div > div.cardapio-modal-header > button").first
                if btn_fechar_modal.is_visible(timeout=2000):
                    btn_fechar_modal.click()
                else:
                    page.mouse.click(10, 10)
            except:
                page.mouse.click(10, 10)
            
            page.wait_for_timeout(600)
            
            try:
                page.click("#cadastro-submenu > li:nth-child(9) > a > span", timeout=3000) 
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(500)
            except:
                pass
            
        log_callback("- Todo o PDF foi processado e cadastrado no sistema!")
        browser.close()