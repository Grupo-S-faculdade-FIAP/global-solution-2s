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

## Grupo GS2

## 👨‍🎓 Integrantes:
- <a href="https://github.com/carolineccorrea">Caroline de Castro Corrêa</a>
- <a href="https://github.com/figueiroa-fiap">Rodrigo Dias Figueiroa</a>
- <a href="https://github.com/EnzF">Enzo França Sader</a>
- <a href="https://github.com/lucasKoyama">Lucas Hideki Oliveira Koyama</a>
- <a href="https://github.com/kyber-me">Tiago Lindgren Curi</a>

## 👩‍🏫 Professores:
### Tutor(a)
- <a href="https://github.com/SabrinaOtoni">Sabrina Otoni</a>
### Coordenador(a)
- <a href="https://www.linkedin.com/in/andregodoichiovato/">Andre Godoi</a>

---

## 📜 Descrição

O **GS2** é uma plataforma de monitoramento climático inteligente que combina visão computacional (YOLOv5), computação em nuvem (AWS) e sensores IoT (ESP32) para detectar padrões de nuvens chuvosas em imagens de satélite e gerar alertas de chuva em tempo real.

O projeto endereça a falta de sistemas acessíveis que integrem imagens de satélite, inteligência artificial e sensores de campo para antecipar eventos climáticos com impacto direto na agricultura e no cotidiano — conectando dados orbitais a ações práticas no solo.

**Principais componentes da solução:**

- **Módulo Computer Vision (CV):** pipeline de captura de imagens de satélite (Windy.com / AWS EC2) com modelo YOLOv5 treinado para detectar padrões de nuvens chuvosas;
- **Módulo Cloud/Backend:** API REST construída com FastAPI, hospedada na AWS (EC2 para captura de imagens + Lambda para processamento serverless + SNS para envio de alertas de chuva em tempo real).
- **Módulo IoT:** ESP32 com sensores de umidade do solo para monitoramento remoto de campo, com dados enviados para a nuvem via HTTP.
- **Módulo Análise de Dados:** armazenamento dos alertas em banco SQL/NoSQL (dia e horário) com visualização em gráficos de barras para identificação de padrões recorrentes de chuva por dia da semana e faixa de horário.

A solução foi desenvolvida como projeto Global Solution da Graduação ON em Inteligência Artificial da FIAP.

---

## 📁 Estrutura de pastas

Dentre os arquivos e pastas presentes na raiz do projeto, definem-se:

- **`docs/`**: Documentação textual do projeto — como: brainstorm, diagramas de arquitetura, desenhos de fluxo, prints, storyboard, estratégia de IA, especificações de hardware (ESP32/Wokwi), atas de reunião e decisões técnicas.

- **`src/`**: Todo o código-fonte desenvolvido — API FastAPI (routers de CV, IoT e Dashboard), scripts de treinamento YOLO, notebooks de exploração e análise de dados, código para ESP32 e modelos serializados.

- **`data/`**: Dados utilizados no projeto — amostras de imagens de satélite (Windy.com), datasets de treino/validação do modelo YOLO (imagens rotuladas de nuvens chuvosas) e registros de alertas para análise posterior.

- **`assets/`**: Imagens e recursos estáticos utilizados na documentação (logo FIAP, etc.).

- **`README.md`**: Arquivo que serve como guia e explicação geral sobre o projeto (o mesmo que você está lendo agora).

---

## 📎 Links e Observações

- **Repositório GitHub:** https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s
- **Vídeo de demonstração (5min):** *(link a ser adicionado após gravação)*
- **Dashboard (Streamlit):** *(link a ser adicionado após deploy)*
- **API Backend (AWS):** *(link a ser adicionado após deploy)*

**Decisões técnicas relevantes:**
- YOLOv5 foi escolhido para detecção de padrões de nuvens chuvosas por ser estado da arte em detecção de objetos, com suporte a pipelines customizados de rotulagem e treino.
- AWS EC2 realiza a captura periódica de imagens de satélite; AWS Lambda processa os dados de forma serverless; AWS SNS dispara as notificações de alerta de chuva.
- O banco de dados SQL/NoSQL armazena dia e horário de cada alerta, alimentando a análise de padrões de recorrência de chuva.
- Config de segredos via `pydantic-settings` + `.env` — nenhum segredo hard-coded no código.

**Observações gerais:**
- Este projeto foi desenvolvido no contexto da Global Solution da FIAP (Graduação ON em IA)

---

## 🔧 Como executar o código

### Pré-requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) ou `pip`
- Arquivo `.env` configurado (copiar `.env.example` e preencher as variáveis)

### Instalação e execução

```bash
# Clone o repositório
git clone git@github.com:Grupo-S-faculdade-FIAP/global-solution-2s.git
cd global-solution-2s

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
