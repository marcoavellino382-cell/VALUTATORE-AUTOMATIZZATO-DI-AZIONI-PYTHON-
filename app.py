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

# Funzione ausiliaria per estrarre in modo sicuro i dati dai bilanci di yfinance (case-insensitive)
def get_financial_row(df, target_name):
    if df is None or df.empty:
        return None
    for idx in df.index:
        if target_name.lower().replace(" ", "") in str(idx).lower().replace(" ", ""):
            return df.loc[idx]
    return None

if ticker_input:
    try:
        with st.spinner(f"Scaricamento e analisi dei dati finanziari per {ticker_input}..."):
            ticker = yf.Ticker(ticker_input)
            
            # Estrazione Info Generali e Fast Info (molto più stabili nel 2026)
            info = ticker.info if ticker.info else {}
            fast_info = ticker.fast_info if hasattr(ticker, 'fast_info') else {}
            
            company_name = info.get('longName', ticker_input)
            currency = info.get('currency', 'USD')
            
            # Recupero stabile del prezzo corrente da history o fast_info
            historical_data = ticker.history(period="1d")
            if not historical_data.empty:
                current_price = historical_data['Close'].iloc[-1]
            else:
                current_price = fast_info.get('lastPrice', info.get('currentPrice', 0.0))
            
            # Estrazione dei 3 bilanci fondamentali
            cash_flow = ticker.cashflow
            financials = ticker.financials
            balance_sheet = ticker.balancesheet
            
        # Controllo flussi di cassa con la nuova funzione sicura
        fcf_row = get_financial_row(cash_flow, 'Free Cash Flow')
        
        if fcf_row is None or fcf_row.dropna().empty:
            st.error("⚠️ Dati sui flussi di cassa liberi (Free Cash Flow) non disponibili per questo Ticker.")
        else:
            st.header(f"{company_name} ({ticker_input})")
            
            # --- CALCOLO STRUTTURATO E SICURO DELLE METRICHE CHIAVE ---
            # Numero di azioni circolanti estrapolate dal modulo veloce o info standard
            shares_outstanding = fast_info.get('sharesOutstanding', info.get('sharesOutstanding', None))
            
            # Market Cap sicuro
            market_cap = fast_info.get('marketCap', info.get('marketCap', None))
            if (market_cap is None or market_cap == 0) and shares_outstanding and current_price:
                market_cap = current_price * shares_outstanding
                
            # Calcolo dinamico e sicuro del P/E Ratio
            pe_ratio = info.get('trailingPE', None)
            net_income_row = get_financial_row(financials, 'Net Income')
            if (pe_ratio is None or pe_ratio == 0) and net_income_row is not None:
                latest_net_income = net_income_row.iloc[0] # Prende l'anno più recente
                if latest_net_income and latest_net_income != 0 and market_cap:
                    pe_ratio = market_cap / latest_net_income

            # Calcolo dinamico dell'EV/EBITDA cercato riga per riga
            ev_ebitda = info.get('enterpriseToEbitda', None)
            ebitda_row = get_financial_row(financials, 'EBITDA')
            
            if (ev_ebitda is None or ev_ebitda == 0) and market_cap and ebitda_row is not None:
                cash_row = get_financial_row(balance_sheet, 'Cash And Cash Equivalents')
                debt_row = get_financial_row(balance_sheet, 'Total Debt')
                
                total_cash = cash_row.iloc[0] if cash_row is not None else 0
                total_debt = debt_row.iloc[0] if debt_row is not None else 0
                enterprise_value = market_cap + total_debt - total_cash
                
                latest_ebitda = ebitda_row.iloc[0]
                if latest_ebitda and latest_ebitda != 0:
                    ev_ebitda = enterprise_value / latest_ebitda

            # Formattazione per la UI
            market_cap_display = f"{int(market_cap):,}" if market_cap else "N/D"
            pe_display = f"{pe_ratio:.2f}" if (isinstance(pe_ratio, (int, float)) and pe_ratio > 0) else "N/D"
            ebitda_display = f"{ev_ebitda:.2f}" if (isinstance(ev_ebitda, (int, float)) and ev_ebitda > 0) else "N/D"
            
            # --- SEZIONE VISIVA METRICHE CHIAVE ---
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Prezzo Attuale", f"{current_price:.2f} {currency}")
            col2.metric("Market Cap", market_cap_display)
            col3.metric("P/E Ratio", pe_display)
            col4.metric("EV/EBITDA", ebitda_display)
            
            st.divider()
            
            # --- ANALISI DEI FLUSSI DI CASSA ---
            st.subheader("📊 Storico dei Flussi di Cassa Reali (Ultimi 4 Anni)")
            fcf_series = fcf_row.dropna()
            fcf_series = fcf_series.iloc[::-1] # Ordine cronologico
            
            fcf_df = pd.DataFrame(fcf_series).rename(columns={fcf_series.name: f'Free Cash Flow ({currency})'})
            fcf_df.index = pd.to_datetime(fcf_df.index).strftime('%Y')
            st.dataframe(fcf_df.T, use_container_width=True)
            
            latest_fcf = fcf_series.iloc[-1]
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
            
            cash_row_dcf = get_financial_row(balance_sheet, 'Cash And Cash Equivalents')
            debt_row_dcf = get_financial_row(balance_sheet, 'Total Debt')
            total_cash_dcf = cash_row_dcf.iloc[0] if cash_row_dcf is not None else 0
            total_debt_dcf = debt_row_dcf.iloc[0] if debt_row_dcf is not None else 0
            
            equity_value = enterprise_value_dcf + total_cash_dcf - total_debt_dcf
            
            if not shares_outstanding:
                st.error("Impossibile recuperare le azioni circolanti per completare il calcolo per singola azione.")
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
                    st.success(f"🟢 L'azione risulta **SOTTOVALUTATA**. Il valore intrinseco stimato è superiore del {margin_of_safety:.1f}% rispetto al prezzo attuale.")
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
                    st.write(f"**Cassa Totale estratta:** {int(total_cash_dcf):,} {currency} | **Debito Totale estratto:** {int(total_debt_dcf):,} {currency}")
                    st.write(f"**Azioni in circolazione (Shares Outstanding):** {int(shares_outstanding):,}")

                    except Exception as e:
                    st.error(f"Errore durante l'elaborazione dei dati: {e}")
