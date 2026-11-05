# 71 BI Mtz — Sistema de Controle de Acesso de Civis

Sistema web local para controle diário de entrada e saída de civis no 71º Batalhão de Infantaria Motorizado.

## Instalação

### 1. Pré-requisitos
- Python 3.8 ou superior instalado
- pip disponível

### 2. Instalar dependências
```bash
pip install -r requirements.txt
```

### 3. Iniciar o sistema
```bash
python app.py
```

### 4. Acessar
Abra o navegador e acesse: **http://localhost:5000**

---

## Funcionalidades

### 📋 Relação do Dia (`/relacao`)
- Adicionar civis à relação do dia atual
- Busca rápida por nome ou CPF
- Registrar seção visitada, número do crachá, horário de entrada e saída
- Botão rápido para registrar saída com horário atual
- Imprimir a relação formatada (A4, pronto para assinar)

### 👤 Cadastro de Pessoas (`/pessoas`)
- Cadastrar, editar e excluir pessoas
- Campos: Nome, CPF, Empresa/Vínculo, Telefone, Observações
- Filtro por nome ou CPF

### 🖨️ Impressão
- Relatório formatado com cabeçalho oficial
- Campos para assinatura do responsável e oficial de dia
- Otimizado para papel A4

---

## Estrutura do Projeto
```
71bi/
├── app.py              # Aplicação Flask + rotas + banco de dados
├── requirements.txt    # Dependências Python
├── database.db         # Banco SQLite (criado automaticamente)
├── README.md
└── templates/
    ├── base.html       # Layout base (navbar, estilos)
    ├── relacao.html    # Relação do dia
    ├── cadastro.html   # Novo cadastro
    ├── pessoas.html    # Lista de pessoas
    └── imprimir.html   # Página de impressão
```

---

## Backup dos Dados
O banco de dados fica em `database.db` na pasta do projeto.
Para fazer backup, basta copiar este arquivo para outro local.

---

## Seções padrão cadastradas
- S1 - Pessoal
- S2 - Inteligência
- S3 - Operações
- S4 - Logística
- S6 - Comunicações
- Comando
- Companhia de Comando
- Outro

Para adicionar mais seções, acesse diretamente o banco SQLite ou solicite ao desenvolvedor.
