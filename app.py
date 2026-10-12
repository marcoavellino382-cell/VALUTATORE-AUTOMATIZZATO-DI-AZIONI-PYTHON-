import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Valutatore Azioni DCF", page_icon="📈", layout="wide")

st.title("📈 Valutatore Automatizzato di Azioni (Modello DCF)")
st.markdown("""
Questo strumento scarica automaticamente i dati di bilancio storici da **Yahoo Finance** 
e calcola il valore intrinseco di un'azione utilizzando un modello di **Discounted Cash Flow (DCF)** semplificato.
""")

# Sidebar per l'input dell'utente
st.sidebar.header("Parametri di Input")
ticker_input = st.sidebar.text_input("Inserisci il Ticker (es. AAPL, MSFT, NVDA)", value="AAPL").upper().strip()

# Parametri finanziari modificabili dall'utente
st.sidebar.subheader("Assunzioni del Modello")
wacc = st.sidebar.slider("Tasso di Sconto / WACC (%)", min_value=4.0, max_value=20.0, value=9.0, step=0.5) / 100
growth_rate = st.sidebar.slider("Tasso di Crescita FCF stimato (Primi 5 anni %)", min_value=-10.0, max_value=30.0, value=8.0, step=0.5) / 100
perpetual_growth = st.sidebar.slider("Tasso di Crescita Perpetuo (%)", min_value=1.0, max_value=5.0, value=2.5, step=0.1) / 100

if ticker_input:
    try:
        with st.spinner(f"Scaricamento e analisi dei dati finanziari per {ticker_input}..."):
            # Inizializzazione ticker yfinance
            ticker = yf.Ticker(ticker_input)
            
            # Estrazione Info Generali
            info = ticker.info if ticker.info else {}
            company_name = info.get('longName', ticker_input)
            currency = info.get('currency', 'USD')
            
            # 1. Recupero stabile del prezzo corrente
            historical_data = ticker.history(period="1d")
            if not historical_data.empty:
                current_price = historical_data['Close'].iloc[-1]
            else:
                current_price = info.get('currentPrice', 0.0)
            
            # Estrazione dei 3 bilanci fondamentali
            cash_flow = ticker.cashflow
            financials = ticker.financials
            balance_sheet = ticker.balancesheet
            
        if cash_flow.empty or 'Free Cash Flow' not in cash_flow.index:
            st.error("⚠️ Dati sui flussi di cassa liberi (Free Cash Flow) non disponibili per questo Ticker.")
        else:
            st.header(f"{company_name} ({ticker_input})")
            
            # --- CALCOLO MATEMATICO DELLE METRICHE MANCANTI (CON CORREZIONE .ILOC) ---
            shares_outstanding = info.get('sharesOutstanding', None)
            
            # Se manca il Market Cap, lo calcoliamo noi: Prezzo x Azioni Circolanti
            market_cap = info.get('marketCap', None)
            if (market_cap is None or market_cap == 0) and shares_outstanding and current_price:
                market_cap = current_price * shares_outstanding
                
            # Calcolo dinamico del P/E Ratio (Market Cap / Net Income dell'anno più recente)
            pe_ratio = info.get('trailingPE', None)
            if pe_ratio is None and not financials.empty and 'Net Income' in financials.index:
                latest_net_income = financials.loc['Net Income'].iloc[0] # .iloc[0] prende il primo anno (il più recente)
                if latest_net_income and latest_net_income != 0 and market_cap:
                    pe_ratio = market_cap / latest_net_income

            # Calcolo dinamico dell'EV/EBITDA
            ev_ebitda = info.get('enterpriseToEbitda', None)
            if ev_ebitda is None and market_cap and not financials.empty and 'EBITDA' in financials.index:
                # Estraiamo Cassa e Debiti in modo sicuro dall'ultimo anno disponibile
                total_cash = balance_sheet.loc['Cash And Cash Equivalents'].iloc[0] if 'Cash And Cash Equivalents' in balance_sheet.index else 0
                total_debt = balance_sheet.loc['Total Debt'].iloc[0] if 'Total Debt' in balance_sheet.index else 0
                enterprise_value = market_cap + total_debt - total_cash
                
                latest_ebitda = financials.loc['EBITDA'].iloc[0] # .iloc[0] prende l'EBITDA più recente
                if latest_ebitda and latest_ebitda != 0:
                    ev_ebitda = enterprise_value / latest_ebitda

            # Formattazione visiva sicura dei dati calcolati
            market_cap_display = f"{int(market_cap):,}" if market_cap else "N/D"
            pe_display = f"{pe_ratio:.2f}" if (isinstance(pe_ratio, (int, float)) and pe_ratio > 0) else "N/D"
            ebitda_display = f"{ev_ebitda:.2f}" if (isinstance(ev_ebitda, (int, float)) and ev_ebitda > 0) else "N/D"
            
            # --- SEZIONE METRICHE CHIAVE VISIVE ---
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Prezzo Attuale", f"{current_price:.2f} {currency}")
            col2.metric("Market Cap", market_cap_display)
            col3.metric("P/E Ratio", pe_display)
            col4.metric("EV/EBITDA", ebitda_display)
            
            st.divider()
            
            # --- ANALISI DEI FLUSSI DI CASSA ---
            st.subheader("📊 Storico dei Flussi di Cassa Reali (Ultimi 4 Anni)")
            fcf_series = cash_flow.loc['Free Cash Flow'].dropna()
            fcf_series = fcf_series.iloc[::-1] # Ordine cronologico dal meno recente al più recente
            
            fcf_df = pd.DataFrame(fcf_series).rename(columns={'Free Cash Flow': f'Free Cash Flow ({currency})'})
            fcf_df.index = fcf_df.index.strftime('%Y')
            st.dataframe(fcf_df.T, use_container_width=True)
            
            latest_fcf = fcf_series.iloc[-1] # L'ultimo elemento della serie cronologica è il più recente
            st.info(f"Base di partenza per la proiezione (Ultimo FCF disponibile): **{latest_fcf:,} {currency}**")
            
            # --- CALCOLO DEL MODELLO DCF ---
            future_years = [f"Anno {i+1}" for i in range(5)]
            projected_fcf = []
            discounted_fcf = []
            
            current_fcf_projection = latest_fcf
            for i in range(5):
                current_fcf_projection *= (1 + growth_rate)
                projected_fcf.append(current_fcf_projection)
                discount_factor = (1 + wacc) ** (i + 1)
                discounted_fcf.append(current_fcf_projection / discount_factor)
            
            terminal_value = (projected_fcf[-1] * (1 + perpetual_growth)) / (wacc - perpetual_growth)
            discounted_terminal_value = terminal_value / ((1 + wacc) ** 5)
            enterprise_value_dcf = sum(discounted_fcf) + discounted_terminal_value
            
            total_cash = balance_sheet.loc['Cash And Cash Equivalents'].iloc[0] if 'Cash And Cash Equivalents' in balance_sheet.index else 0
            total_debt = balance_sheet.loc['Total Debt'].iloc[0] if 'Total Debt' in balance_sheet.index else 0
            equity_value = enterprise_value_dcf + total_cash - total_debt
            
            if not shares_outstanding:
                st.error("Impossibile recuperare le azioni circolanti (`sharesOutstanding`) per il calcolo finale.")
            else:
                intrinsic_value = equity_value / shares_outstanding
                margin_of_safety = ((intrinsic_value - current_price) / intrinsic_value) * 100
                
                # --- PRESENTAZIONE RISULTATI VALUTAZIONE ---
                st.subheader("⚖️ Risultato della Valutazione DCF")
                
                res_col1, res_col2, res_col3 = st.columns(3)
                res_col1.metric("Valore Intrinseco Stimato", f"{intrinsic_value:.2f} {currency}")
                res_col2.metric("Prezzo di Mercato Attuale", f"{current_price:.2f} {currency}")
                
                if intrinsic_value > current_price:
                    res_col3.metric("Margine di Sicurezza", f"+{margin_of_safety:.1f}%", delta_color="normal")
                    st.success(f"🟢 L'azione resulta **SOTTOVALUTATA**. Il valore intrinseco stimato è superiore del {margin_of_safety:.1f}% rispetto al prezzo attuale.")
                else:
                    res_col3.metric("Margine di Sicurezza", f"{margin_of_safety:.1f}%", delta_color="inverse")
                    st.warning(f"🔴 L'azione risulta **SOPRAVALUTATA**. Il prezzo attuale di mercato supera la stima del valore intrinseco.")
                
                with st.expander("🔍 Mostra i dettagli matematici dei flussi calcolati"):
                    dcf_data = {
                        "Anno": future_years,
                        "FCF Proiettato": [f"{int(x):,}" for x in projected_fcf],
                        "FCF Attualizzato": [f"{int(x):,}" for x in discounted_fcf]
                    }
                    st.table(pd.DataFrame(dcf_data))
                    st.write(f"**Terminal Value stimato all'anno 5:** {int(terminal_value):,} {currency}")
                    st.write(f"**Valore Attuale del Terminal Value:** {int(discounted_terminal_value):,} {currency}")
                    st.write(f"**Cassa Totale estratta:** {int(total_cash):,} {currency} | **Debito Totale estratto:** {int(total_debt):,} {currency}")
                    st.write(f"**Azioni in circolazione (Shares Outstanding):** {int(shares_outstanding):,}")
                    
    except Exception as e:
        st.error(f"Errore durante l'elaborazione dei dati: {e}")
