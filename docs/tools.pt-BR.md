# Os scripts de `tools/`

[English](tools.md) · [简体中文](tools.zh-CN.md) · [繁體中文](tools.zh-TW.md) · [日本語](tools.ja.md) · [한국어](tools.ko.md) · [Español](tools.es.md) · [Français](tools.fr.md) · [Deutsch](tools.de.md) · Português (Brasil) · [Русский](tools.ru.md)

Os scripts de `tools/` são para quem executa o personagent a partir de um clone. Eles não são instalados com o pacote e leem `.env` e `runtime/` do clone. Execute-os com o interpretador do clone, a partir da raiz do repositório:

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

As tarefas do dia a dia são subcomandos do `personagent` em vez de scripts: `personagent doctor`, `personagent learned` e `personagent eval`. Para testar uma mudança de prompt, use `personagent chat`. Para medi-la, use `personagent eval`. `personagent eval --suite memory` é executado offline com respostas de consolidação roteirizadas, 21 casos por idioma, e não precisa de chave; nesta versão, todos são atendidos. As outras suítes chamam um modelo.

| Script | O que faz | Precisa de | Chama um modelo | Status |
|---|---|---|---|---|
| `import_stickers_folder.py` | Importa uma pasta de imagens para a biblioteca de figurinhas e marca cada uma, para que uma biblioteca nova não comece vazia. `--dry-run` mostra as contagens e `--no-tag` só copia os arquivos | Uma pasta de imagens, mais `VISION_MODEL`, `VISION_API_KEY` e `VISION_BASE_URL` para marcar | Sim, uma chamada de visão por imagem, a menos que você passe `--dry-run` ou `--no-tag` | Com suporte |
| `bootstrap_from_history.py` | Dá a uma implantação nova um início único a partir do histórico de um grupo do QQ. Cria o perfil de figurinhas e tamanho de mensagens do administrador e salva na biblioteca as figurinhas que vê | O servidor HTTP do NapCat, um cliente de QQ de terceiros, em `QQ_ONEBOT_URL` (obrigatório), e grupos do QQ em `ACCESS_GROUPS` ou `--group` | Não. O modelo de visão do bot em execução marca depois as figurinhas salvas | Experimental, só QQ e NapCat |
| `sticker_holdout_eval.py` | Mede a estabilidade e a precisão do filtro de aprovação de figurinhas com figurinhas que você rotulou à mão | `runtime/holdout.jsonl` (formato em `tools/holdout.example.jsonl`) e as três configurações `VISION_*` | Sim, imagens × `--runs` (padrão 5) chamadas de visão, cerca de 150 para 30 imagens | Experimental |
| `package_smoke.py` | Verifica de ponta a ponta um comando `personagent` instalado: versão, `init --no-input`, `chat`, `run` com `/health` e `doctor --json` | Um `personagent` instalado (`--personagent PATH`) e nada mais | Não, um servidor substituto responde | Com suporte. A CI executa no Linux e no Windows |
| `welcome_smoke.py` | Verifica de ponta a ponta a página local instalada: `start --no-browser`, salvar uma chave, uma conversa com o personagem real, uma segunda abertura que reaproveita a página e uma saída limpa | Um `personagent` instalado (`--personagent PATH`) e nada mais | Não, o mesmo servidor substituto responde | Com suporte. A CI executa no Linux e no Windows |
| `window_smoke.py` | Abre a janela real do aplicativo em uma pasta inicial temporária, configura a página e conversa dentro da janela, depois fecha a janela | `personagent` instalado com o extra do aplicativo (`pip install "personagent[app]"`) no macOS e no Linux; no Linux, também uma tela, como `xvfb-run` | Não, o mesmo servidor substituto responde | Com suporte. A CI executa no Linux, no macOS e no Windows |
| `release_notes.py` | Confere uma tag de versão com `pyproject.toml` e imprime a seção do CHANGELOG dessa versão | A tag, como `v1.1.0` | Não | Com suporte. O fluxo de publicação executa |
| `locale_gaps.py` | Conta, para cada idioma em `persona_agent/locales/`, quantas frases do assistente de configuração, da conversa no terminal e da demonstração têm tradução. Com um código de idioma, como `ja`, imprime as que ainda faltam e apareceriam em inglês | Nada | Não | Com suporte. `tests/test_locales.py` falha se faltar alguma |

Os scripts experimentais são auxiliares de pesquisa e manutenção e podem mudar ou ser removidos sem período de descontinuação. Os scripts que chamam um modelo gastam crédito da conta no seu `.env`; leia `--help` primeiro e teste `--dry-run` onde existir.
