#include <JAson.mqh>
#include <Trade\Trade.mqh>

CTrade trade;
CJAVal JsonValue;

string filename = "signals.json";

input string lot_rules = "XAUUSD=1,USDJPY=1.5,EURUSD=0.10";
input double default_lot = 0.01;
input string inpcomment = "TeleSignal"; // Comment

int OnInit(){
   Print("Signal EA start");
   ReadSignalsAndExecute();
   return(INIT_SUCCEEDED);
}

void OnTick(){
   ReadSignalsAndExecute();
}


void ReadSignalsAndExecute(){
   ResetLastError();

   CJAVal root;
   string json_text;
   
   int handle=FileOpen(filename, FILE_READ|FILE_TXT|FILE_ANSI);
   if(handle == INVALID_HANDLE){
      Print("❌ Cannot open file: ", filename);
      Print("Error code ", GetLastError()); 
      return;
   }

   while(!FileIsEnding(handle))
        json_text += FileReadString(handle);

   FileClose(handle);   
   if(!root.Deserialize(json_text)){
      Print("❌ Failed to JSON.Deserialize");
      return;
   }

   int count = root.Size();

   for(int i = 0; i < count; i++){
      
      CJAVal sig = root[i];

      string symbol  = sig["symbol"].ToStr();
      int type       = sig["type"].ToInt();
      double vol     = GetLotForSymbol(sig["symbol"].ToStr());
      double entry   = sig["entry"].ToDbl();
      double sl      = sig["sl"].ToDbl();
      string date    = sig["date"].ToStr();
      string comment = inpcomment;
      long index     = sig["index"].ToInt();

      bool processed = sig["processed"].ToBool();
      if(processed) continue;

      string final_comment = comment + "#" + IntegerToString(index);
      CJAVal tpArr = sig["tp"];
      double tps[];
      string tps_str="";
      int tpCount = tpArr.Size();
      ArrayResize(tps, tpCount);
      for(int j=0; j<tpCount; j++){
         tps[j] = tpArr[j].ToDbl();
         tps_str += NormalizeDouble(DoubleToString(tpArr[j].ToDbl()), SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + " ";
      }
      ArraySort(tps);

      if(!IsToday(date) || IsSignalAlreadyExecuted(final_comment)){
         continue;
      }    

      Print(
         "Signal #", i, " → ",
         "Symbol=", symbol,
         ", Type=", type == 1 ? "BUY" : "SELL",
         ", Volume=", vol,
         ", Entry=", entry,
         ", SL=", sl,
         ", TPs=", tps_str,
         ", Date: ", date,
         ", Comment: ", final_comment
      );

      bool opened = OpenTrade(symbol, type, vol, entry, sl, tps[0], 0, final_comment);
      if(opened){
         MarkSignalAsProcessed((int)index);
      }

   }
}

bool OpenTrade(string symbol, int type, double volume, double entry, double sl, double tp, int magic, string comment)
{
   if(!SymbolSelect(symbol, true)){
      Print("Symbole invalide: ", symbol);
      return false;
   }

   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);

   ENUM_ORDER_TYPE order_type;
   double price;

   // ===== BUY =====
   if(type == 1)
   {
      if(entry <= 0) // Market
      {
         order_type = ORDER_TYPE_BUY;
         price = ask;
      }
      else if(entry < ask) // Buy Limit
      {
         order_type = ORDER_TYPE_BUY_LIMIT;
         price = entry;
      }
      else // entry > ask → Buy Stop
      {
         order_type = ORDER_TYPE_BUY_STOP;
         price = entry;
      }
   }
   // ===== SELL =====
   else if(type == 2)
   {
      if(entry <= 0) // Market
      {
         order_type = ORDER_TYPE_SELL;
         price = bid;
      }
      else if(entry > bid) // Sell Limit
      {
         order_type = ORDER_TYPE_SELL_LIMIT;
         price = entry;
      }
      else // entry < bid → Sell Stop
      {
         order_type = ORDER_TYPE_SELL_STOP;
         price = entry;
      }
   }
   else
   {
      return false;
   }

   bool result;
   // ===== EXECUTION =====
   if(order_type == ORDER_TYPE_BUY || order_type == ORDER_TYPE_SELL)
   {
      result = trade.PositionOpen(symbol, order_type, volume, price, sl, tp, comment);
   }
   else
   {
      result = trade.OrderOpen(symbol, order_type, volume, price, price,sl, tp, ORDER_TIME_GTC, 0, comment);
   }

   if(!result)
   {
      Print("Erreur ouverture trade: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
      return false;
   }
   else
   {
      Print("Ordre envoyé: ", EnumToString(order_type), " @ ", price);
      return true;
   }
}

bool IsToday(string date_str){
    // date_str: "YYYY-MM-DD HH:MM:SS"
    datetime signal_time = StringToTime(date_str);
    if(signal_time <= 0)
        return false;

    datetime now = TimeCurrent();

    MqlDateTime sig, cur;
    TimeToStruct(signal_time, sig);
    TimeToStruct(now, cur);

    return (sig.year  == cur.year &&
            sig.mon   == cur.mon  &&
            sig.day   == cur.day);
}

bool IsSignalAlreadyExecuted(string expected)
{
   // ===== 1. CHECK POSITIONS OUVERTES =====
   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket))
         continue;

      string comment = PositionGetString(POSITION_COMMENT);
      if(StringFind(comment, expected) != -1)
         return true;
   }

   // ===== 2. CHECK ORDRES EN ATTENTE =====
   int orders = OrdersTotal();
   for(int i = 0; i < orders; i++)
   {
      ulong ticket = OrderGetTicket(i);
      if(!OrderSelect(ticket))
         continue;

      string comment = OrderGetString(ORDER_COMMENT);
      if(StringFind(comment, expected) != -1)
         return true;
   }

   // ===== 3. CHECK HISTORIQUE (AUJOURD'HUI) =====
   datetime today_start = StringToTime(TimeToString(TimeCurrent(), TIME_DATE));
   datetime now = TimeCurrent();

   if(!HistorySelect(today_start, now))
      return false;

   int deals = HistoryDealsTotal();
   for(int i = 0; i < deals; i++)
   {
      ulong deal_ticket = HistoryDealGetTicket(i);
      if(deal_ticket == 0)
         continue;

      string comment = HistoryDealGetString(deal_ticket, DEAL_COMMENT);
      if(StringFind(comment, expected) != -1)
         return true;
   }

   return false;
}

double GetLotForSymbol(string symbol)
{
   string rules[];
   int count = StringSplit(lot_rules, ',', rules);

   for(int i = 0; i < count; i++)
   {
      string pair[];
      
      if(StringSplit(rules[i], '=', pair) != 2)
         continue;

      string rule_symbol = pair[0];
      double rule_lot = StringToDouble(pair[1]);

      // Nettoyage espaces éventuels
      StringTrimLeft(rule_symbol);
      StringTrimRight(rule_symbol);

      if(rule_symbol == symbol)
         return rule_lot;
   }

   return default_lot;
}

void MarkSignalAsProcessed(int signal_index)
{
   CJAVal root;
   string json_text;

   int handle = FileOpen(filename, FILE_READ|FILE_TXT|FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return;

   while(!FileIsEnding(handle))
      json_text += FileReadString(handle);

   FileClose(handle);

   if(!root.Deserialize(json_text))
      return;

   for(int i = 0; i < root.Size(); i++)
   {
      if(root[i]["index"].ToInt() == signal_index)
      {
         root[i]["processed"] = true;
         break;
      }
   }

   int count = root.Size();
   string json = "[\n";
   for(int i = 0; i < count; i++)
   {
      CJAVal sig   = root[i];
      CJAVal tpArr = sig["tp"];
      int tpCount  = tpArr.Size();

      json += "    {\n";
      json += "        \"symbol\": \""   + sig["symbol"].ToStr() + "\",\n";
      json += "        \"type\": "       + IntegerToString(sig["type"].ToInt()) + ",\n";
      json += "        \"entry\": "      + DoubleToString(sig["entry"].ToDbl()) + ",\n";
      json += "        \"sl\": "         + DoubleToString(sig["sl"].ToDbl()) + ",\n";
      json += "        \"tp\": [";
      for(int j = 0; j < tpCount; j++){
         json += DoubleToString(tpArr[j].ToDbl());
         if(j < tpCount - 1) json += ", ";
      }
      json += "],\n";
      json += "        \"date\": \""     + sig["date"].ToStr() + "\",\n";
      json += "        \"index\": "      + IntegerToString((int)sig["index"].ToInt()) + ",\n";
      json += "        \"processed\": "  + (sig["processed"].ToBool() ? "true" : "false") + "\n";
      json += "    }";
      if(i < count - 1) json += ",";
      json += "\n";
   }
   json += "]";

   handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return;
   FileWriteString(handle, json);
   FileClose(handle);
}
