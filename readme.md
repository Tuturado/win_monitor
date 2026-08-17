# 🖥️ Winmonitor

O **Winmonitor** é uma aplicação leve e em tempo real para monitoramento do sistema no Windows. O servidor coleta estatísticas de desempenho do computador e disponibiliza um painel web responsivo, permitindo acompanhar o uso do PC diretamente pelo navegador do celular via rede local.

---

## 🚀 Funcionalidades

* **Monitoramento de CPU:** Medição de precisão equivalente ao Gerenciador de Tarefas do Windows (via PDH/ctypes).
* **Uso de Memória RAM:** Porcentagem de utilização atualizada segundo a segundo.
* **Atividade de Disco (E/S):** Cálculo em tempo real da taxa de ocupação ativa do HD/SSD.
* **Tráfego de Rede:** Leitura de velocidade de Download e Upload (`KB/s` ou `MB/s`).
* **Suporte Híbrido a GPU:** Detecção automática de GPUs **NVIDIA** (via NVML) e fallback para **AMD/Intel** (via contadores nativos do Windows).
* **Tratamento de GPU em Standby:** Identificação visual do estado de repouso de placas dedicadas em notebooks.
* **Conexão Rápida via QR Code:** Geração automática de QR Code no terminal para conexão instantânea pela câmera do celular.
* **Painel Responsivo com Cores Dinâmicas:** Mudança automática das cores dos cards (normal, alerta e crítico) com base na carga do hardware.
* **Executável Standalone:** Compilado em um único arquivo `.exe` portátil sem necessidade de instalação prévia do Python.

---

## 🛠️ Tecnologias Utilizadas

### **Backend**
* **[Python 3](https://www.python.org/):** Linguagem principal da aplicação.
* **[FastAPI](https://fastapi.tiangolo.com/):** Framework web assíncrono de alta performance para disponibilizar as APIs REST.
* **[Uvicorn](https://uvicorn.dev/):** Servidor ASGI leve para execução do servidor.
* **[psutil](https://github.com/giampaolo/psutil):** Coleta de métricas do sistema (CPU, RAM, Disco e Rede).
* **[pynvml](https://pypi.org/project/pynvml/):** Biblioteca para leitura de sensores de placas de vídeo NVIDIA.
* **[qrcode](https://pypi.org/project/qrcode/):** Renderização do QR Code em arte ASCII no terminal.

### **Frontend**
* **HTML5 / CSS3 / JavaScript (Vanilla):** Interface leve, sem frameworks pesados, com design escuro (*dark mode*) e consumo assíncrono via `fetch()`.

### **Empacotamento**
* **[PyInstaller](https://pyinstaller.org/):** Compilação do código Python e assets estáticos em um executável autônomo.

---

## 📂 Estrutura do Projeto

```text
pc-monitor-pro/
│
├── server.py             # Código principal do servidor FastAPI e thread de coleta
├── icone.ico             # Ícone personalizado do executável
├── static/
│   └── index.html        # Interface web do painel de monitoramento
└── README.md             # Documentação do projeto