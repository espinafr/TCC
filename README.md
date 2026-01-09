# Timby - Uma Plataforma para Pais

![Status](https://img.shields.io/badge/status-archived-orangd.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.x-blue.svg)
![Tailwind CSS](https://img.shields.io/badge/tailwind%20css-3.x-blue.svg)
![JavaScript](https://img.shields.io/badge/javascript-ES6+-yellow.svg)
![Docker](https://img.shields.io/badge/docker-20.x-blue.svg)

O Timby é uma plataforma social com foco em parentalidade, criada para conectar pais e responsáveis. A plataforma visa democratizar o conhecimento sobre criação de filhos, oferecendo uma rede de apoio e uma vasta biblioteca de recursos e dicas.

Além de ser um espaço informativo, o Timby se diferencia por seu sistema de missões, que sugere atividades e momentos de conexão entre pais e filhos. O objetivo é fortalecer os laços familiares e oferecer suporte prático, adaptado a diferentes rotinas e necessidades.

## Começando

Você pode executar o projeto usando Docker ou localmente com um ambiente virtual Python.

### Pré-requisitos

*   [Docker](https://www.docker.com/get-started) (para a configuração com Docker)
*   [Python 3.10+](https://www.python.org/downloads/) (para a configuração local)

### Executando com Docker

1.  **Clone o repositório:**

    ```bash
    git clone https://github.com/seu-usuario/timby.git
    cd timby
    ```

2.  **Construa e execute o contêiner Docker:**

    ```bash
    docker-compose up --build
    ```

3.  **Acesse a aplicação:**

    Abra seu navegador e acesse `http://localhost:5000`.

### Executando Localmente

1.  **Clone o repositório:**

    ```bash
    git clone https://github.com/seu-usuario/timby.git
    cd timby
    ```

2.  **Crie e ative um ambiente virtual:**

    ```bash
    # Para Windows
    python -m venv venv
    .\venv\Scripts\activate

    # Para macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Execute a aplicação:**

    ```bash
    flask run
    ```

5.  **Acesse a aplicação:**

    Abra seu navegador e acesse `http://localhost:5000`.

## Contribuições

Este projeto foi desenvolvido como um Trabalho de Conclusão de Curso (TCC). No momento, contribuições diretas via pull request não estão sendo aceitas.

No entanto, sinta-se à vontade para explorar o código, testar a aplicação e relatar quaisquer bugs ou sugestões abrindo uma **Issue** aqui no GitHub. Todo feedback é bem-vindo!
