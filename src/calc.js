(function(){
  var CAP = window.RC_CAP; // {rate, label}
  function getRate(){try{var v=parseFloat(localStorage.getItem("rc_rate"));if(v>0&&v<200)return v}catch(e){}return CAP.rate}
  function setRate(v){try{v===null?localStorage.removeItem("rc_rate"):localStorage.setItem("rc_rate",String(v))}catch(e){}}
  var rate=getRate();

  function money(p){return p<100?(p<10?p.toFixed(1):String(Math.round(p)))+"p":"£"+(p/100).toFixed(2)}
  function pounds(p){return "£"+(p>=10000?Math.round(p/100).toLocaleString("en-GB"):(p/100).toFixed(2))}
  function mins(m){m=+m;return m<60?(m%1?m.toFixed(1):m)+" min":(Math.floor(m/60)+" h"+(m%60?" "+Math.round(m%60)+" min":""))}
  var $=function(id){return document.getElementById(id)};

  // ---- rate chip + dialog (every page)
  var chip=$("rateChip"),dlg=$("rateDlg");
  function chipText(){chip.textContent=rate.toFixed(2)+"p/kWh"+(rate===CAP.rate?"":" (yours)")}
  function openRate(){$("rateInput").value=rate.toFixed(2);if(dlg.showModal)dlg.showModal();else dlg.setAttribute("open","")}
  function closeRate(){dlg.close?dlg.close():dlg.removeAttribute("open")}
  chip.addEventListener("click",openRate);
  document.querySelectorAll("[data-rate]").forEach(function(b){b.addEventListener("click",openRate)});
  $("rateClose").addEventListener("click",closeRate);
  $("rateSave").addEventListener("click",function(){
    var v=parseFloat($("rateInput").value);
    if(v>0&&v<200){rate=Math.round(v*100)/100;setRate(rate===CAP.rate?null:rate);closeRate();refresh()}
  });
  $("rateReset").addEventListener("click",function(){rate=CAP.rate;setRate(null);closeRate();refresh()});

  // ---- placeholders
  document.querySelectorAll("[data-proto]").forEach(function(b){b.addEventListener("click",function(){
    b.parentElement.querySelector(".msg").textContent="Preview: this will link to a partner once accounts are set up."})});
  document.querySelectorAll("form[data-email]").forEach(function(f){f.addEventListener("submit",function(e){
    e.preventDefault();f.nextElementSibling.textContent="Preview: sign-up isn't connected yet, so nothing was saved."})});

  // ---- tiles and lists on index pages: data-kwh (per use) / data-kwhy (per year)
  function refreshTiles(){
    document.querySelectorAll("[data-kwh],[data-kwhy]").forEach(function(el){
      if(el.dataset.kwh)el.textContent=money(+el.dataset.kwh*rate)+" per "+el.dataset.unit;
      else el.textContent=pounds(+el.dataset.kwhy*rate)+" a year";
    });
    document.querySelectorAll("[data-rateval]").forEach(function(el){el.textContent=rate.toFixed(2)+"p/kWh"});
  }

  // ---- appliance calculator
  var D=null,el=$("appdata");
  if(el){try{D=JSON.parse(el.textContent)}catch(e){}}
  var ids=[];
  var fmts={w:function(v){return v+" W"},m:mins,u:function(v){return v},k:function(v){return (+v).toFixed(2)+" kWh"},y:function(v){return v+" kWh"},mth:function(v){return v+(v==1?" month":" months")}};
  function ctl(id,label,a,val,help){
    return '<div class="ctl"><label for="'+id+'">'+label+'<output id="'+id+'o"></output></label>'+
      '<input type="range" id="'+id+'" min="'+a[0]+'" max="'+a[1]+'" step="'+a[3]+'" value="'+val+'">'+(help?'<small>'+help+'</small>':'')+'</div>';
  }
  function cap(s){return s.charAt(0).toUpperCase()+s.slice(1)}
  function build(){
    var h="";
    if(D.mode==="power"){
      h+=ctl("w","Power",D.w,D.w[2],"Check the label, plug or manual. It's shown in watts (W).");
      h+=ctl("m","Time on per "+D.unit,D.m,D.m[2]);
      h+=ctl("u",(D.unit==="use"?"Uses":cap(D.unit)+"s")+" per week",D.u,D.u[2]);
      ids=["w","m","u"];
    }else if(D.mode==="cycle"){
      h+=ctl("k","Energy per cycle",D.k,D.k[2],"The energy label shows kWh per cycle, or per 100 cycles (divide by 100).");
      h+=ctl("u","Cycles per week",D.u,D.u[2]);
      ids=["k","u"];
    }else{
      h+=ctl("y","Energy use per year",D.y,D.y[2],"Printed on the energy label as kWh/annum.");
      ids=["y"];
    }
    if(D.mode!=="annual"&&D.mo<12){h+=ctl("mth","Months used per year",[1,12,D.mo,1],D.mo);ids.push("mth")}
    $("controls").innerHTML=h;
    ids.forEach(function(i){$(i).addEventListener("input",render)});
    $("resetBtn").addEventListener("click",function(){
      var d={w:D.w&&D.w[2],m:D.m&&D.m[2],u:D.u&&D.u[2],k:D.k&&D.k[2],y:D.y&&D.y[2],mth:D.mo};
      ids.forEach(function(i){$(i).value=d[i]});render();
    });
  }
  function read(){var s={};ids.forEach(function(i){s[i]=parseFloat($(i).value)});return s}
  function render(){
    if(!D)return;
    var s=read();ids.forEach(function(i){$(i+"o").textContent=fmts[i](s[i])});
    var mo=s.mth||D.mo,kUse=null,kWeek,kYear;
    if(D.mode==="power"){kUse=s.w/1000*(s.m/60)*D.duty;kWeek=kUse*s.u;kYear=kWeek*52*mo/12}
    else if(D.mode==="cycle"){kUse=s.k;kWeek=s.k*s.u;kYear=kWeek*52*mo/12}
    else{kYear=s.y;kWeek=kYear/52}
    var year=kYear*rate,rows="";
    if(D.mode==="annual"){$("ansLab").textContent="Cost per year";$("ansBig").textContent=pounds(year);$("ansSub").textContent="About "+pounds(year/12)+" a month at "+rate.toFixed(2)+"p/kWh."}
    else{
      $("ansLab").textContent="Cost per "+D.unit;$("ansBig").textContent=money(kUse*rate);
      $("ansSub").textContent="About "+pounds(year)+" a year at "+s.u+" "+D.unit+(s.u==1?"":"s")+" a week"+(mo<12?", "+mo+" months a year.":".");
    }
    if(D.mode==="power")rows+="<tr><td>Per hour running</td><td>"+money(s.w/1000*D.duty*rate)+"</td></tr>";
    if(kUse!==null)rows+="<tr><td>Per "+D.unit+"</td><td>"+money(kUse*rate)+"</td></tr>";
    rows+="<tr><td>Per week (in use)</td><td>"+money(kWeek*rate)+"</td></tr><tr><td>Per month (average)</td><td>"+pounds(year/12)+"</td></tr><tr><td>Per year</td><td>"+pounds(year)+"</td></tr>";
    rows+='<tr class="sep"><td colspan="2">Electricity used</td></tr>';
    if(kUse!==null)rows+='<tr class="kwh"><td>Per '+D.unit+'</td><td>'+kUse.toFixed(2)+' kWh</td></tr>';
    rows+='<tr class="kwh"><td>Per year</td><td>'+Math.round(kYear).toLocaleString("en-GB")+' kWh</td></tr>';
    $("tbl").innerHTML=rows;
    $("rateNow").textContent=rate.toFixed(2)+"p/kWh";
    $("rateWhat").textContent=rate===CAP.rate?CAP.label:"Your own rate, saved on this device.";
    var hp=$("hpCost");
    if(hp){var y2=1.8*s.u*52*mo/12*rate;hp.textContent=pounds(y2);$("hpSave").textContent=pounds(Math.max(0,year-y2))}
  }
  function refresh(){chipText();refreshTiles();render()}
  // ---- sortable lists (home page categories, category tables)
  var btns=document.querySelectorAll(".sortbtn");
  function sortBy(key,dir){
    document.querySelectorAll(".sortable").forEach(function(box){
      var items=Array.prototype.slice.call(box.children);
      items.sort(function(a,b){
        var r=key==="name"?a.dataset.name.localeCompare(b.dataset.name):(+a.dataset.year)-(+b.dataset.year);
        return dir==="asc"?r:-r;
      });
      items.forEach(function(el){box.appendChild(el)});
    });
    btns.forEach(function(b){
      var on=b.dataset.key===key;b.classList.toggle("on",on);
      b.querySelector(".arr").textContent=on?(dir==="asc"?"▲":"▼"):"";
      if(on)b.dataset.dir=dir;
    });
  }
  btns.forEach(function(b){b.addEventListener("click",function(){
    var dir=b.classList.contains("on")?(b.dataset.dir==="asc"?"desc":"asc"):b.dataset.dir;
    sortBy(b.dataset.key,dir);
  })});

  if(D)build();
  refresh();
})();
