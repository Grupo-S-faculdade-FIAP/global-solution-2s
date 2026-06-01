# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href="https://www.fiap.com.br/">
  <img src="assets/logo-fiap.png" 
       alt="FIAP - Faculdade de Informática e Administração Paulista" 
       width="40%">
</a>
</p>

<br>

# global-solution-2s

## Grupo TerraSense

## 👨‍🎓 Integrantes:
- <a href="https://www.linkedin.com/in/caroline-de-castro-correa/">Caroline de Castro Corrêa</a>
- <a href="https://www.linkedin.com/in/rodrigo-dias-figueiroa/">Rodrigo Dias Figueiroa</a>
- <a href="https://www.linkedin.com/in/enzo-franca-sader/">Enzo França Sader</a>
- <a href="https://www.linkedin.com/in/lucas-hideki-oliveira-koyama/">Lucas Hideki Oliveira Koyama</a>
- <a href="https://www.linkedin.com/in/tiago-lindgren-curi/">Tiago Lindgren Curi</a>

## 👩‍🏫 Professores:
### Tutor(a)
- <a href="https://www.linkedin.com/in/caique-nonato/">Caique Nonato</a>
### Coordenador(a)
- <a href="https://www.linkedin.com/in/andregodoichiovato/">Andre Godoi</a>

---

## 📜 Descrição

O **TerraSense** é uma plataforma de inteligência ambiental e agrícola que combina dados de satélite, visão computacional (YOLOv8) e sensores IoT (ESP32) para monitorar o clima, detectar queimadas e desmatamento, e prever riscos agrícolas — conectando a economia espacial ao impacto direto na Terra.

O projeto endereça a fragmentação e a demora no acesso a inteligência ambiental acionável: os dados de satélite existem, mas não são processados, analisados e visualizados de forma integrada e acessível para pesquisadores, produtores rurais, órgãos de monitoramento ambiental e gestores de risco.

**Principais componentes da solução:**

- **Módulo Computer Vision (CV):** pipeline de ingestão de imagens de satélite (NASA FIRMS / INPE) com modelo YOLOv8 treinado para detecção de focos de queimada e áreas desmatadas.
- **Módulo Machine Learning (ML):** modelo de regressão/classificação para previsão de risco agrícola (seca, geada, produtividade) utilizando dados climáticos e de satélite.
- **Módulo Cloud/Backend:** API REST construída com FastAPI, hospedada na AWS (Lambda + API Gateway), conectada a banco de dados PostgreSQL (RDS) e DynamoDB (dados IoT).
- **Módulo Dashboard/Frontend:** visualização climática em tempo real via widget Windy API integrado a um painel Streamlit com dados e alertas ambientais.
- **Módulo IoT:** ESP32 com MicroPython coletando dados de temperatura, umidade e solo, enviando para AWS IoT Core via HTTP.

A solução foi desenvolvida como projeto Global Solution da Graduação ON em Inteligência Artificial da FIAP.

---

## 📁 Estrutura de pastas

Dentre os arquivos e pastas presentes na raiz do projeto, definem-se:

- **`docs/`**: Documentação textual do projeto — brainstorm, diagramas de arquitetura, desenhos de fluxo, prints, storyboard, estratégia de IA, especificações de hardware (ESP32/Wokwi), atas de reunião e decisões técnicas.

- **`src/`**: Todo o código-fonte desenvolvido — API FastAPI (routers de CV, ML, IoT e Dashboard), scripts de treinamento YOLO, notebooks de exploração de dados, código MicroPython para ESP32 e modelos serializados.

- **`data/`**: Dados utilizados no projeto — amostras de imagens de satélite (FIRMS/INPE), CSVs climáticos, datasets de treino/validação do modelo YOLO e bases sintéticas para testes.

- **`Ir Além/`**: Arquivos referentes às atividades de aprofundamento e experimentações extras, além do escopo mínimo da entrega principal.

- **`assets/`**: Imagens e recursos estáticos utilizados na documentação (logo FIAP, etc.).

- **`README.md`**: Arquivo que serve como guia e explicação geral sobre o projeto (o mesmo que você está lendo agora).

---

## 📎 Links e Observações

- **Repositório GitHub:** https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s
- **Vídeo de demonstração:** *(link a ser adicionado após gravação)*
- **Dataset NASA FIRMS:** https://firms.modaps.eosdis.nasa.gov/
- **Dashboard (Streamlit):** *(link a ser adicionado após deploy)*
- **API Backend (AWS):** *(link a ser adicionado após deploy)*

**Decisões técnicas relevantes:**
- YOLOv8 (Ultralytics) foi escolhido para detecção de queimadas por ser estado da arte em detecção de objetos, com boa documentação e suporte a datasets públicos (FIRMS/INPE).
- Windy API utilizada via widget embarcado (plano free não disponibiliza REST completo), cobrindo a visualização climática em mapa de forma gratuita.
- Arquitetura serverless na AWS (Lambda + API Gateway) reduz custo operacional; o free tier é suficiente para o POC.
- Config de segredos via `pydantic-settings` + `.env` — nenhum segredo hardcodado no código.

**Observações gerais:**
- Este projeto foi desenvolvido no contexto da Global Solution da FIAP (Graduação ON em IA) e aceita participação na avaliação da competição.

---

## 🔧 Como executar o código

### Pré-requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) ou `pip`
- Arquivo `.env` configurado (copiar `.env.example` e preencher as variáveis)

### Instalação e execução

```bash
# Clone o repositório
git clone <URL-DO-REPOSITÓRIO>
cd global-solutions

# Instale as dependências
cd src
pip install -r requirements.txt
# ou, usando o Makefile:
make install

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas chaves

# Inicie a API
make run
# ou:
uvicorn app.main:app --reload

# Rode os testes
make test
# ou:
pytest tests/ -v
```

A API estará disponível em `http://localhost:8000`.  
Documentação interativa (Swagger): `http://localhost:8000/docs`

---

## 🗃 Histórico de lançamentos

* 0.1.0 - 01/06/2026
    * Scaffold inicial FastAPI com routers para CV, ML, IoT e Dashboard
    * Configuração via pydantic-settings + .env
    * Estrutura de pastas conforme template TIAO-2026
    * Testes base com pytest

---

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/SabrinaOtoni/TEMPLATE-FIAP-GRAD-ON-IA">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">FIAP</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
