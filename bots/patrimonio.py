import re
import time
from playwright.sync_api import sync_playwright

# -------------------------------------------------------------------------
# FUNCOES AUXILIARES DE NAVEGACAO E FORMULARIO
# -------------------------------------------------------------------------

def clicar_texto(page, texto, timeout=3000):
    """Localiza qualquer elemento pelo texto visivel com fallbacks rapidos."""
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
    """Fecha qualquer modal ou aviso residual na tela sem estragar o CSS do site."""
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

    # Aqui estava o vilao que escondia o modal. Agora ele apenas limpa a classe, sem dar display: none forçado
    page.evaluate(r"""() => {
        const modais = document.querySelectorAll('.modal.show, #modalNovoEq, #modalEquipamento, .modal-overlay');
        modais.forEach(m => {
            m.classList.remove('show', 'active');
            m.style.display = ''; // Limpa o estilo em vez de forcar none
        });
        const backdrops = document.querySelectorAll('.modal-backdrop, .swal2-container');
        backdrops.forEach(b => b.remove());
        document.body.classList.remove('modal-open');
    }""")
    page.wait_for_timeout(200)


def preencher_dentro_do_modal(page, rotulo, valor):
    """Preenche estritamente dentro do modal que estiver aberto (#modalNovoEq ou #modalEquipamento)."""
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
    """Seleciona dropdown de Local ou Setor com correspondencia exata ignorando acentos."""
    if not texto_opcao:
        return False

    rotulo_lower = rotulo.lower()
    tipo = "setor" if "setor" in rotulo_lower else "local"

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
    """Verifica se o setor ja existe no dropdown ignorando acentos."""
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
    """Cria um setor novo."""
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
    """Clica em salvar no modal que estiver ativo."""
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

def executar_bot_patrimonio(texto_bruto, log_callback, url, usuario, senha, unidade_selecionada):
    linhas = texto_bruto.strip().splitlines()
    setor_atual = None
    equipamentos = []

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

        # Interceptamos especificamente o dialog nativo do navegador e clicamos em OK
        dialog_duplicado = {"ocorreu": False, "mensagem": ""}
        def tratar_dialog(dialog):
            msg = dialog.message.lower()
            if any(termo in msg for termo in ["já cadastrado", "ja cadastrado", "duplicad", "deseja editar"]):
                dialog_duplicado["ocorreu"] = True
                dialog_duplicado["mensagem"] = dialog.message
                dialog.accept() # Clica em OK
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

        cadastrados = 0
        editados = 0

        for idx, item in enumerate(equipamentos, start=1):
            dialog_duplicado["ocorreu"] = False
            dialog_duplicado["mensagem"] = ""

            log_callback(f"[{idx}/{len(equipamentos)}] Processando: {item['nome']} (Cod: {item['codigo']}) - Setor: [{item['setor']}]")
            
            fechar_modal_equipamento(page)

            # 1. Garante que o setor existe antes de cadastrar
            if not verificar_se_setor_existe(page, item["setor"]):
                cadastrar_novo_setor(page, item["setor"], log_callback)

            # 2. Clica EXATAMENTE no ID do botao Novo Equipamento e espera a tela subir
            page.locator("#btnNovoEq").wait_for(state="visible", timeout=3000)
            page.locator("#btnNovoEq").click()
            page.wait_for_timeout(1000) # Pausa garantida para a janela abrir visivelmente

            # 3. Preenche codigo e forca o Tab para disparar a verificacao Ajax
            preencher_dentro_do_modal(page, "Código", item["codigo"])
            page.keyboard.press("Tab")
            
            # ATENÇÃO AQUI: Espera longa para o sistema pesquisar e subir o alert nativo do navegador
            page.wait_for_timeout(1500) 

            # Verifica se estourou algum alerta customizado na tela (SweetAlert) como backup
            alerta_customizado = page.locator('.swal2-confirm, button:has-text("OK")').first
            try:
                if alerta_customizado.is_visible(timeout=500):
                    alerta_customizado.click()
                    dialog_duplicado["ocorreu"] = True
            except Exception:
                pass

            # 4. Checa o resultado da verificacao de duplicidade
            if dialog_duplicado["ocorreu"]:
                log_callback(f"Patrimonio '{item['codigo']}' existente detectado. Atualizando dados...")
                page.wait_for_timeout(800) # Pausa para os dados antigos preencherem a tela antes de sobrescrever
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
            page.wait_for_timeout(500)

            # 5. Salva e aguarda confirmacao
            salvar_modal_ativo(page)
            page.wait_for_timeout(800)

        fechar_modal_equipamento(page)
        log_callback(f"- Concluido: {cadastrados} cadastrados, {editados} editados.")
        browser.close()