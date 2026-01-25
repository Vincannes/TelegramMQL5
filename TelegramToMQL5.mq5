#include <JAson.mqh>
#include <Trade\Trade.mqh>

CTrade trade;
CJAVal JsonValue;

string filename = "signals.json";

input double lot = 0.01; // Lot
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
      double vol     = lot;
      double entry   = sig["entry"].ToDbl();
      double sl      = sig["sl"].ToDbl();
      string date    = sig["date"].ToStr();
      string comment = inpcomment;
      long index     = sig["index"].ToInt();
      
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

      if(!IsToday(date) || IsSignalAlreadyExecuted(final_comment)) continue;

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

      OpenTrade(symbol, type, vol, entry, sl, tps[0], 0, final_comment);
   }
}

void OpenTrade(string symbol, int type, double volume, double entry, double sl, double tp, int magic, string comment){
   double price = 0;
   ENUM_ORDER_TYPE order_type = 0;
   if(type == 1){ // Buy
      order_type = ORDER_TYPE_BUY;
      price = entry > 0 ? entry : SymbolInfoDouble(symbol, SYMBOL_ASK);
   }
   else if(type == 2){ // Sell
      order_type = ORDER_TYPE_SELL;
      price = entry > 0 ? entry : SymbolInfoDouble(symbol, SYMBOL_BID);
   }
   else{
      Print("Type inconnu: ", type);
      return;
   }

   if(!SymbolSelect(symbol,true)){
      Print("Symbole invalide: ", symbol);
      return;
   }

   // Envoi de l'ordre market (ou pending si entry différent)
   bool result = trade.PositionOpen(symbol, order_type, volume, price, sl, tp, comment);
   if(!result){
      Print("Erreur ouverture trade: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
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

bool IsSignalAlreadyExecuted(string expected){
   int total = PositionsTotal();
   for(int i = 0; i < total; i++){
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket))
         continue;

      string comment = PositionGetString(POSITION_COMMENT);
      if(StringFind(comment, expected) != -1)
         return true;
   }

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

