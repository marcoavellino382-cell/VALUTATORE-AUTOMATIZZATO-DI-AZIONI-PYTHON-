# 📈 Valutatore Automatizzato di Azioni (Modello DCF)

Questo progetto è un'applicazione web interattiva realizzata in **Python** e **Streamlit** che permette di calcolare il valore intrinseco di un'azione utilizzando il modello finanziario del **Discounted Cash Flow (DCF)**. 

I dati di bilancio vengono estratti in tempo reale e in modo completamente gratuito tramite l'API di **Yahoo Finance** (`yfinance`).

## 🚀 Funzionalità
- **Estrazione Dati Real-Time:** Download automatico di Prezzo attuale, Market Cap, P/E, EV/EBITDA e degli ultimi 4 anni di Free Cash Flow.
- **Modello DCF Dinamico:** Possibilità di modificare il WACC (Tasso di Sconto), il tasso di crescita dei flussi e il tasso perpetuo tramite slider interattivi.
- **Calcolo del Margine di Sicurezza:** Identificazione immediata se un titolo è Sottovalutato o Sopravalutato rispetto al prezzo di mercato.

## 🛠️ Tecnologie Utilizzate
- **Python 3**
- **Streamlit** (per l'interfaccia utente)
- **yfinance** (per i dati finanziari)
- **Pandas & NumPy** (per la manipolazione dei dati e i calcoli matematici)
