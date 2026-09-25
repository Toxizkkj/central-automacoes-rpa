import re
import time
from playwright.sync_api import sync_playwright

# -------------------------------------------------------------------------
# FUNCOES AUXILIARES DE NAVEGACAO E FORMULARIO
# -------------------------------------------------------------------------

def clicar_texto(page, texto, timeout=3000):
    localizadores = [
        page.get_by_role("button", name=re.compile(texto, re.IGNORECASE)),
        page.get_by_role("link", name=re.compile(texto, re.IGNORECASE)),
        page.locator(f'button:has-text("{texto}")'),
        page.locator(f'a:has-text("{texto}")'),
        page.locator(f'//*[contains(normalize-space(.), "{texto}") and not(self::script) and not(self::style)]').last
    ]

    for loc in localizadores:
        try:
            if loc.is_visible(timeout=300):
                loc.click()
                return
        except Exception:
            continue

    page.evaluate(r"""(txt) => {
        const els = Array.from(document.querySelectorAll('button, a, span, div'));
        for (let el of els) {
            if (el.textContent && el.textContent.trim().toLowerCase().includes(txt.toLowerCase())) {
                el.click();
                return true;
            }
        }
        return false;
    }""", texto)


def fechar_modal_equipamento(page):
    try:
        btn_alerta = page.locator('.swal2-cancel, .swal2-confirm, button:has-text("Não"), button:has-text("Cancelar")')
        if btn_alerta.count() > 0 and btn_alerta.first.is_visible(timeout=200):
            btn_alerta.first.click()
            page.wait_for_timeout(200)
    except Exception:
        pass

    try:
        btn_fechar = page.locator('#btnFecharEq, button:has-text("Fechar"), .modal-header .btn-close, .modal-header .close')
        if btn_fechar.first.is_visible(timeout=250):
            btn_fechar.first.click()
    except Exception:
        pass

    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    page.evaluate(r"""() => {
        const modais = document.querySelectorAll('.modal.show, #modalNovoEq, #modalEquipamento, .modal-overlay');
        modais.forEach(m => {
            m.classList.remove('show', 'active');
            m.style.display = '';
        });
        const backdrops = document.querySelectorAll('.modal-backdrop, .swal2-container');
        backdrops.forEach(b => b.remove());
        document.body.classList.remove('modal-open');
    }""")
    page.wait_for_timeout(200)


def preencher_dentro_do_modal(page, rotulo, valor):
    if valor is None or valor == "":
        return

    page.evaluate(r"""({rotulo, valor}) => {
        let modal = document.querySelector('#modalEquipamento:not([style*="display: none"]), #modalNovoEq:not([style*="display: none"]), .modal-overlay:not([style*="display: none"])');
        if (!modal) {
            modal = document.querySelector('#modalEquipamento, #modalNovoEq, form');
        }
        if (!modal) return;

        const termo = rotulo.toLowerCase();
        let campo = null;

        if (termo.includes('código')) {
            campo = modal.querySelector('#eq_codigo, input[name*="codigo"]');
        } else if (termo.includes('nome')) {
            campo = modal.querySelector('#eq_nome, input[name*="nome"]');
        } else if (termo.includes('marca')) {
            campo = modal.querySelector('#eq_marca, input[name*="marca"]');
        } else if (termo.includes('modelo')) {
            campo = modal.querySelector('#eq_modelo, input[name*="modelo"]');
        }

        if (!campo) {
            const labels = Array.from(modal.querySelectorAll('label, div, span, p'));
            const alvo = labels.find(el => el.textContent.trim().toLowerCase().includes(termo));
            if (alvo) {
                const parent = alvo.closest('.form-group, .col, div, tr') || alvo.parentElement;
                campo = parent ? parent.querySelector('input:not([type="hidden"]), textarea') : null;
            }
        }

        if (campo) {
            campo.value = valor;
            campo.dispatchEvent(new Event('input', { bubbles: true }));
            campo.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }""", {"rotulo": rotulo, "valor": str(valor)})


def selecionar_dentro_do_modal_js(page, rotulo, texto_opcao):
    if not texto_opcao:
        return False

    rotulo_lower = rotulo.lower()
    if "setor" in rotulo_lower:
        tipo = "setor"
    elif "tipo" in rotulo_lower:
        tipo = "tipo"
    else:
        tipo = "local"

    return page.evaluate(r"""({tipo, textoOpcao}) => {
        const norm = (s) => s ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, " ").trim().toLowerCase() : "";

        let modal = document.querySelector('#modalEquipamento:not([style*="display: none"]), #modalNovoEq:not([style*="display: none"]), .modal-overlay:not([style*="display: none"])');
        if (!modal) {
            modal = document.querySelector('#modalEquipamento, #modalNovoEq, form');
        }
        if (!modal) return false;

        let sel = null;
        if (tipo === 'setor') {
            sel = modal.querySelector('#eq_setor, select[name*="setor"]');
        } else if (tipo === 'tipo') {
            sel = modal.querySelector('#eq_tip, select[name*="tip"]');
        } else {
            sel = modal.querySelector('#eq_local, select[name*="local"], select[name*="cliente"]');
        }

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
    }""", {"tipo": tipo, "textoOpcao": str(texto_opcao)})


def verificar_se_setor_existe(page, setor_nome):
    return page.evaluate(r"""(setor) => {
        const norm = (s) => s ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, " ").trim().toLowerCase() : "";
        const sel = document.querySelector('#eq_setor, select[name*="setor"]');
        if (!sel) return false;
        const termo = norm(setor);
        for (let o of sel.options) {
            if (norm(o.text) === termo) return true;
        }
        return false;
    }""", setor_nome)


def cadastrar_novo_setor(page, setor_nome, log_callback):
    log_callback(f"Criando novo setor: [{setor_nome}]")
    fechar_modal_equipamento(page)

    clicar_texto(page, "Adicionar Setor")
    page.wait_for_timeout(600)

    try:
        page.click("#btnNovoSetorEq")
    except Exception:
        clicar_texto(page, "Novo Setor")
    
    page.wait_for_timeout(400)
    page.fill("#setorNome", setor_nome)
    page.wait_for_timeout(300)
    page.click("#modalSetor > div.tec-modal-foot > button.btn.btn-success.tec-btn-sm")
    page.wait_for_timeout(600)
    
    page.click("#modalListaSetores > div.tec-modal-foot > button")
    page.wait_for_timeout(500)


def salvar_modal_ativo(page):
    page.evaluate(r"""() => {
        const modal = document.querySelector('#modalEquipamento:not([style*="display: none"]), #modalNovoEq:not([style*="display: none"]), .modal-overlay:not([style*="display: none"])');
        if (modal) {
            const btn = modal.querySelector('#btnGravarEq, button[type="submit"], .btn-success');
            if (btn) btn.click();
            else {
                const form = modal.querySelector('form');
                if (form) form.submit();
            }
        } else {
            const btn = document.querySelector('#btnGravarEq');
            if (btn) btn.click();
        }
    }""")
    page.wait_for_timeout(800)


# -------------------------------------------------------------------------
# EXECUCAO PRINCIPAL
# -------------------------------------------------------------------------

def executar_bot_patrimonio(texto_bruto, log_callback, url, usuario, senha, unidade_selecionada, tipo_equipamento_selecionado="Equipamento de TI"):
    texto_bruto = texto_bruto.strip()
    
    # ---------------------------------------------------------
    # VERIFICACAO DO COMANDO DE EDICAO EM MASSA
    # ---------------------------------------------------------
    modo_edicao_massa = False
    if texto_bruto.lower().startswith("editar equi"):
        modo_edicao_massa = True

    # Parseamento normal se nao for edicao em massa
    linhas = texto_bruto.splitlines()
    setor_atual = None
    equipamentos = []

    if not modo_edicao_massa:
        for linha in linhas:
            texto = linha.strip()
            if not texto:
                continue

            if texto.endswith(":") or (":" in texto and "-" not in texto):
                setor_atual = texto.replace(":", "").strip()
                setor_atual = re.sub(r'^(setor\s*:?\s*)', '', setor_atual, flags=re.IGNORECASE).strip()
                continue

            if "-" in texto and setor_atual:
                partes = [p.strip() for p in texto.split("-")]

                nome = partes[0] if len(partes) > 0 else ""
                codigo = partes[1] if len(partes) > 1 else ""
                marca = partes[2] if len(partes) > 2 else ""
                modelo = partes[3] if len(partes) > 3 else ""

                equipamentos.append({
                    "setor": setor_atual,
                    "nome": nome,
                    "codigo": codigo,
                    "marca": marca,
                    "modelo": modelo
                })

        if not equipamentos:
            log_callback("- Nenhum equipamento valido encontrado no texto.")
            return

        log_callback(f"- Iniciando processamento de {len(equipamentos)} equipamentos na unidade: [{unidade_selecionada}]...")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False, channel="chrome")
        except Exception:
            try:
                browser = p.chromium.launch(headless=False, channel="msedge")
            except Exception:
                browser = p.chromium.launch(headless=False)

        page = browser.new_page()

        dialog_duplicado = {"ocorreu": False, "mensagem": ""}
        def tratar_dialog(dialog):
            msg = dialog.message.lower()
            if any(termo in msg for termo in ["já cadastrado", "ja cadastrado", "duplicad", "deseja editar"]):
                dialog_duplicado["ocorreu"] = True
                dialog_duplicado["mensagem"] = dialog.message
                dialog.accept()
            else:
                dialog.accept()

        page.on("dialog", tratar_dialog)

        log_callback("Efetuando login...")
        page.goto(url)
        
        page.fill('input[type="email"], input[name="email"], #email', usuario)
        page.fill('input[type="password"], input[name="password"], #senha', senha)
        page.click("button:has-text('Entrar'), button[type='submit'], body > div.login-container > div > form > button")
        page.wait_for_load_state("networkidle")

        try:
            page.wait_for_selector("text='Escolha o sistema para continuar', text='Sistema de Gestão de Chamados', a.chamados, text='Equipamentos'", timeout=4000)
            card_chamados = page.locator("text='Sistema de Gestão de Chamados', a:has-text('Acessar'):near(:text('Gestão de Chamados'))").first
            if card_chamados.is_visible():
                card_chamados.click()
                page.wait_for_load_state("networkidle")
        except Exception:
            pass 

        try:
            page.wait_for_selector("body > section > div > a.system-link.chamados, a.chamados, .system-link", timeout=4000)
        except Exception:
            browser.close()
            raise ValueError("Falha no login! Verifique o e-mail e a senha informados e tente novamente.")

        try:
            btn_pend = page.locator("#modal-pendencias > div > div.portal-actions > button, button:has-text('Fechar')")
            if btn_pend.is_visible(timeout=2000):
                btn_pend.click()
                page.wait_for_timeout(400)
        except Exception:
            pass

        try:
            link_chamados = page.locator("body > section > div > a.system-link.chamados > h2, a.chamados").first
            if link_chamados.is_visible():
                link_chamados.click()
                page.wait_for_load_state("networkidle")
        except Exception:
            pass

        try:
            clicar_texto(page, "Equipamentos", timeout=4000)
        except Exception:
            page.locator('a:has-text("Equipamentos"), span:has-text("Equipamentos")').first.click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(800)

        # ---------------------------------------------------------
        # FLUXO DE EDICAO EM MASSA (MACRO)
        # ---------------------------------------------------------
        if modo_edicao_massa:
            log_callback("Iniciando MODO DE EDIÇÃO EM MASSA (Correção de Tipo de Equipamento)...")
            
            page.wait_for_selector('#tabelaEquipamentos tbody tr, table tbody tr', timeout=5000)
            page.wait_for_timeout(1000)

            linhas = page.locator('#tabelaEquipamentos tbody tr, table tbody tr')
            total = linhas.count()
            log_callback(f"Total de registros identificados na tela: {total}")
            
            termos_ti = [
                "notebook", "desktop", "no break", "nobreak", "impressora", 
                "monitor", "roteador", "switch", "televisão", "televisao", 
                "tv", "etiquetadora", "loadbalance", "estabilizador"
            ]
            
            editados_massa = 0
            for i in range(total):
                linha = linhas.nth(i)
                nome_texto = linha.inner_text().lower()
                
                is_ti = any(termo in nome_texto for termo in termos_ti)
                tipo_alvo = "Equipamento de TI" if is_ti else "Equipamento da manutenção de nutrição"
                
                # Clica EXATAMENTE no botao com a classe .btn-editar-eq dentro da celula de acoes
                btn_editar = linha.locator('td.acoes-cell button.btn-editar-eq').first
                try:
                    btn_editar.click(force=True)
                except Exception:
                    continue
                
                page.wait_for_selector('#modalEquipamento, #modalNovoEq', state="attached", timeout=4000)
                page.wait_for_timeout(400)
                
                selecionar_dentro_do_modal_js(page, "tipo", tipo_alvo)
                page.wait_for_timeout(300)
                
                salvar_modal_ativo(page)
                page.wait_for_timeout(600)
                
                editados_massa += 1
                if editados_massa % 5 == 0:
                    log_callback(f"Progresso: {editados_massa}/{total} concluídos...")
                
            log_callback(f"Edição em massa finalizada. {editados_massa} itens ajustados.")
            browser.close()
            return
        
        # ---------------------------------------------------------
        # FLUXO DE INSERCAO NORMAL
        # ---------------------------------------------------------
        cadastrados = 0
        editados = 0

        for idx, item in enumerate(equipamentos, start=1):
            dialog_duplicado["ocorreu"] = False
            dialog_duplicado["mensagem"] = ""

            log_callback(f"[{idx}/{len(equipamentos)}] Processando: {item['nome']} (Cod: {item['codigo']}) - Setor: [{item['setor']}]")
            
            fechar_modal_equipamento(page)

            if not verificar_se_setor_existe(page, item["setor"]):
                cadastrar_novo_setor(page, item["setor"], log_callback)

            page.locator("#btnNovoEq").wait_for(state="visible", timeout=3000)
            page.locator("#btnNovoEq").click()
            page.wait_for_timeout(1000) 

            # Preenche codigo
            preencher_dentro_do_modal(page, "Código", item["codigo"])
            page.keyboard.press("Tab")
            page.wait_for_timeout(300)

            # Preenche tipo de equipamento e dispara o segundo Tab
            selecionar_dentro_do_modal_js(page, "tipo", tipo_equipamento_selecionado)
            page.wait_for_timeout(300)
            page.keyboard.press("Tab") 
            
            page.wait_for_timeout(1500) 

            alerta_customizado = page.locator('.swal2-confirm, button:has-text("OK")').first
            try:
                if alerta_customizado.is_visible(timeout=500):
                    alerta_customizado.click()
                    dialog_duplicado["ocorreu"] = True
            except Exception:
                pass

            if dialog_duplicado["ocorreu"]:
                log_callback(f"Patrimonio '{item['codigo']}' existente detectado. Atualizando dados...")
                page.wait_for_timeout(800) 
                editados += 1
            else:
                cadastrados += 1

            preencher_dentro_do_modal(page, "Nome", item["nome"])
            page.wait_for_timeout(150)
            preencher_dentro_do_modal(page, "Marca", item["marca"])
            page.wait_for_timeout(150)
            preencher_dentro_do_modal(page, "Modelo", item["modelo"])
            page.wait_for_timeout(150)

            selecionar_dentro_do_modal_js(page, "Local", unidade_selecionada)
            page.wait_for_timeout(150)
            sucesso_setor = selecionar_dentro_do_modal_js(page, "Setor", item["setor"])
            if not sucesso_setor:
                log_callback(f"Aviso: Setor [{item['setor']}] nao foi encontrado no menu suspenso.")
            page.wait_for_timeout(400)

            salvar_modal_ativo(page)
            page.wait_for_timeout(600)

        fechar_modal_equipamento(page)
        log_callback(f"- Concluido: {cadastrados} cadastrados, {editados} editados.")
        browser.close()