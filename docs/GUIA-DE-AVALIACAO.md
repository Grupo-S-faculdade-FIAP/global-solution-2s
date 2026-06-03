## Como usar o guia:
Nosso grupo copiou literalmente as secções **"A solução poderá abordar temas como"** e **"O que esperamos da resposta"** e demos um "check" em cada item que cobrimos na solução - além disso colocamos quem foi o responsável de cada parte, facilitando a compreensão de como cobrimos o que foi solicitado. Espero que ajude, obrigado!

## A solução poderá abordar temas como:
- [x] Sistemas inteligentes de monitoramento climático utilizando dados espaciais;
- [x] Aplicações de visão computacional para análise de imagens orbitais;
- [x] Soluções com redes neurais para previsão de eventos, clima ou produção agrícola;
- [ ] Plataformas cognitivas para análise de grandes volumes de dados espaciais;
- [ ] Sistemas autônomos e sensores inteligentes para ambientes extremos;
- [x] Aplicações em nuvem integradas a dados de satélite;
- [x] Soluções com AWS, Lambda, APIs e AWS serviços cognitivos;
- [x] Plataformas de recomendação e análise preditiva;
- [x] Sistemas de detecção, classificação e segmentação de objetos;
- [x] Aplicações de IoT e ESP32 para monitoramento remoto;
- [x] Soluções sustentáveis e inteligentes inspiradas na exploração espacial.


## O que esperamos da resposta:
- Aplicabilidade e clareza na resolução do problema proposto;
  - [LUCAS]() fazer um bom README.md e video de 5minutos explicando a solução
- Uso criativo e coerente de *Inteligência Artificial, **computação em nuvem* e *análise de dados*;
  - [LUCAS]() *Inteligência Artificial*: reconhecimento de imagem com YOLO para identificar padrões de nuvens chuvosas em imagens de satélite do site windy.com
  - [LUCAS]() *Computação em nuvem*: AWS Lambda para processar os dados de satélite e gerar alertas de chuva em tempo real com SNS e lambda para enviar notificações
  - [CAROL]() *Análise de dados*: plotar em gráfico de barras o padrão de quando tem alerta de chuva, dias da semana e horário
- Demonstração de habilidades técnicas desenvolvidas ao longo do curso;
- Integração entre *Machine Learning, **visão computacional, **sensores*, automação ou aplicações cognitivas;
  - [LUCAS]() *Machine Learning*: treinamento de um modelo YOLO para detectar padrões de nuvens chuvosas em imagens de satélite
  - [LUCAS]() *Visão computacional*: uso do modelo YOLO para análise de imagens de satélite e detecção de padrões de nuvens chuvosas
  - [RODRIGO]() *Sensores*: integração de sensores de umidade do solo para monitoramento remoto usando ESP32
- Aplicação prática de conceitos vistos em aula, como redes neurais, *YOLO, **pipelines de dados (captura e rotulagem para treino do YOLO), **AWS, **computação serverless, **ESP32, **APIs cognitivas, **SQL/NoSQL*, serviços cognitivos e análise de dados em tempo real;
  - [LUCAS]() *YOLO*: treinamento e implementação de um modelo para detecção de padrões de nuvens chuvosas em imagens de satélite
  - [LUCAS]() *pipelines de dados*: captura de imagens de satélite, rotulagem para treino do modelo YOLO
  - [LUCAS]() *AWS: upload manual de screenshots do Windy.com para S3, AWS Lambda (serverless*) acionado via S3 trigger para processamento de dados e AWS SNS para envio de alertas
  - [RODRIGO]() *ESP32*: integração de sensores de umidade do solo para monitoramento remoto
  - [LUCAS]() *SQL/NoSQL*: armazenamento do dia e horário dos alertas de chuva em banco de dados para análise posterior
- Planejamento e documentação organizada da solução;
  - [LUCAS]() fazer um bom *README.md* explicando a solução
- Comunicação visual clara e apresentação estruturada;
  - [ENZO]() criar um *vídeo de 5 minutos* explicando a solução
- Trabalho colaborativo e interdisciplinar.
  - Integrantes:
    - [Enzo França Sader]()
      - Fará o **vídeo de 5min**;
    - [Caroline de Castro Corrêa]()
      - **Análise de dados:** plotar em gráfico de barras o padrão de quando tem alerta de chuva, dias da semana e horário
      - Code reviewer
    - [Rodrigo Dias Figueiroa]()
      - **ESP32:** Integração de sensores de umidade do solo para monitoramento remoto usando ESP32
    - [Lucas Hideki Oliveira Koyama]()
      - **pipeline de dados:** Coleta de imagens de satélite e rotulagem para treino do modelo YOLO
      - **YOLO:** treino do modelo YOLO e análise das imagens de satélite
      - **AWS:** configurou a nuvem AWS para upload manual de screenshots do Windy.com para S3, AWS Lambda (serverless*) acionado via S3 trigger para processamento de dados e AWS SNS para envio de alertas e AWS DynamoDB para guardar dados dos alertas para posterior analise de frequência de chuvas
      - **NoSQL:** armazenar em banco AWS DynamoDB tabela "iot" as mensagens de alerta de chuva (dia da mensagem e horário) para uso em posterior analise de dados
      - **README.md** organizado
    - [Tiago Lindgren Curi]()
      - Code reviewer / orientações técnicas com AWS