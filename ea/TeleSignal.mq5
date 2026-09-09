//+------------------------------------------------------------------+
//|                                                     TeleSignal.mq5 |
//|                                         Copyright 2025, YourName |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, YourName"
#property link      "https://mql5.com"
#property version   "1.10"

// --- Inputs
input string messageInit = "Test Message in Init"; // Message init
input string chat_ID = ""; // User ID
input string botTkn = "";  // Bot Token

//--- Snapshot of a tracked position: kept so SL/TP changes can be
//--- detected tick to tick, and P&L computed after the close.
struct PosSnapshot
{
   ulong  ticket;
   string symbol;
   int    digits;
   double pip;          // 1 pip in price units (10 points on 3/5-digit symbols)
   long   type;         // POSITION_TYPE_BUY / POSITION_TYPE_SELL
   double open_price;
   double sl;
   double tp;
   bool   be_notified;  // BreakEven already announced — avoid duplicate alerts
};

PosSnapshot g_tracked[];

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    SendMessage(messageInit);
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    CheckPositionsChanges();
}

//+------------------------------------------------------------------+
//| Percent-encoding UTF-8 pour le corps du message Telegram         |
//+------------------------------------------------------------------+
string UrlEncode(const string text)
{
   uchar bytes[];
   int len = StringToCharArray(text, bytes, 0, -1, CP_UTF8) - 1; // -1 : drop trailing \0
   string out = "";

   for(int i = 0; i < len; i++)
   {
      uchar c = bytes[i];
      if((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
         (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.' || c == '~')
         out += CharToString(c);
      else
         out += StringFormat("%%%02X", c);
   }
   return out;
}

//+------------------------------------------------------------------+
//| Fonction d'envoi Telegram                                        |
//+------------------------------------------------------------------+
void SendMessage(string message)
{
   char data[];
   char result[];
   string headers;

   const string baseUrl = "https://api.telegram.org/";
   // Message is URL-encoded: it contains line breaks and emojis that would
   // otherwise break the WebRequest URL.
   string url = baseUrl + "bot" + botTkn + "/sendMessage?chat_id=" + chat_ID + "&text=" + UrlEncode(message);

   ResetLastError();
   int code = WebRequest("POST", url, "", 10000, data, result, headers);

   if(code == -1)
   {
      PrintFormat("❌ WebRequest échouée. Erreur %d", GetLastError());
   }
   else{
      Print(url);
   }
}

//+------------------------------------------------------------------+
//| Taille d'un pip pour le symbole                                  |
//+------------------------------------------------------------------+
double PipSize(const string symbol, const int digits)
{
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   // Broker point is a tenth of a pip on fractional forex quotes (3/5 digits)
   // and on cent-quoted symbols like XAUUSD (2 digits): 4015 -> 4020 = 50 pips.
   return (digits == 2 || digits == 3 || digits == 5) ? point * 10.0 : point;
}

//+------------------------------------------------------------------+
//| Index du ticket dans g_tracked, -1 si absent                     |
//+------------------------------------------------------------------+
int FindTracked(const ulong ticket)
{
   for(int i = 0; i < ArraySize(g_tracked); i++)
      if(g_tracked[i].ticket == ticket)
         return i;
   return -1;
}

//+------------------------------------------------------------------+
//| Prix de clôture réel, lu dans l'historique des deals             |
//+------------------------------------------------------------------+
double GetClosePrice(const ulong ticket)
{
   if(!HistorySelectByPosition(ticket)) return 0.0;

   int deals = HistoryDealsTotal();
   for(int i = deals - 1; i >= 0; i--)   // last OUT deal = final close
   {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0) continue;

      long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
      if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY)
         return HistoryDealGetDouble(deal, DEAL_PRICE);
   }
   return 0.0;
}

//+------------------------------------------------------------------+
//| Vérifie les positions                                            |
//+------------------------------------------------------------------+
void CheckPositionsChanges()
{
    int total = PositionsTotal();

    //--- New positions + SL/TP changes -------------------------------
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;

        string sym        = PositionGetString(POSITION_SYMBOL);
        int    digits     = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
        double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
        double sl         = PositionGetDouble(POSITION_SL);
        double tp         = PositionGetDouble(POSITION_TP);
        long   type       = PositionGetInteger(POSITION_TYPE);

        int idx = FindTracked(ticket);

        if(idx == -1)
        {
            //--- Nouvelle position -----------------------------------
            string side = (type == POSITION_TYPE_BUY ? "BUY" : "SELL");

            string msg;
            StringConcatenate(msg,
                "🚨 ", side, " ", sym, " : ", DoubleToString(open_price, digits), "\n\n",
                "🔴 StopLoss : ",   DoubleToString(sl, digits), "\n",
                "🟢 TakeProfit : ", DoubleToString(tp, digits), "\n\n",
                "Disclaimer : Il ne s'agit en aucun cas d'un conseil financier ",
                "mais uniquement d'une alerte à titre indicative."
            );
            SendMessage(msg);

            int n = ArraySize(g_tracked);
            ArrayResize(g_tracked, n + 1);
            g_tracked[n].ticket      = ticket;
            g_tracked[n].symbol      = sym;
            g_tracked[n].digits      = digits;
            g_tracked[n].pip         = PipSize(sym, digits);
            g_tracked[n].type        = type;
            g_tracked[n].open_price  = open_price;
            g_tracked[n].sl          = sl;
            g_tracked[n].tp          = tp;
            // A position opened directly at BE needs no later BE alert.
            g_tracked[n].be_notified = (sl > 0 &&
                                        MathAbs(sl - open_price) < g_tracked[n].pip * 0.1);
            continue;
        }

        //--- Position déjà suivie : SL modifié ? ---------------------
        double point = SymbolInfoDouble(sym, SYMBOL_POINT);
        if(MathAbs(sl - g_tracked[idx].sl) > point * 0.5)
        {
            // BreakEven = SL ramené au prix d'entrée (tolérance 1/10 de pip).
            bool is_be = (sl > 0 && MathAbs(sl - open_price) < g_tracked[idx].pip * 0.1);

            if(is_be && !g_tracked[idx].be_notified)
            {
                SendMessage("⚖️ BreakEven placé sur " + sym + " (SL = prix d'entrée)");
                g_tracked[idx].be_notified = true;
            }
            else if(!is_be)
            {
                SendMessage("✏️ Nouveau StopLoss " + sym + " : " + DoubleToString(sl, digits));
                g_tracked[idx].be_notified = false; // SL repart d'ailleurs qu'au BE
            }

            g_tracked[idx].sl = sl;
        }

        g_tracked[idx].tp = tp;
    }

    //--- Closed positions --------------------------------------------
    for(int j = ArraySize(g_tracked) - 1; j >= 0; j--)
    {
        ulong ticket = g_tracked[j].ticket;

        if(PositionSelectByTicket(ticket)) continue; // toujours ouverte

        double close_price = GetClosePrice(ticket);
        double pips = 0.0;

        if(close_price > 0 && g_tracked[j].pip > 0)
        {
            double diff = (g_tracked[j].type == POSITION_TYPE_BUY)
                          ? (close_price - g_tracked[j].open_price)
                          : (g_tracked[j].open_price - close_price);
            pips = diff / g_tracked[j].pip;
        }

        SendMessage("🔒 Clôturer la position " + DoubleToString(pips, 1) + " pips");

        for(int k = j; k < ArraySize(g_tracked) - 1; k++)
            g_tracked[k] = g_tracked[k + 1];
        ArrayResize(g_tracked, ArraySize(g_tracked) - 1);
    }
}
