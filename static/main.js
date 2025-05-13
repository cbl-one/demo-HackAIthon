// static/main.js
async function send(){
    const inp = document.getElementById("inp");
    const txt = inp.value.trim();
    if(!txt) return;
    append("You", txt);
    inp.value = "";
    const res = await fetch("/message", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({text: txt})
    }).then(r=>r.json());
    append(res.agent, res.response);
    document.getElementById("upl").style.display = res.needsUpload ? "block" : "none";
  }
  
  async function upload(){
    const file = document.getElementById("img").files[0];
    if(!file) return;
    const fd = new FormData();
    fd.append("image", file);
    const res = await fetch("/upload", {method:"POST", body: fd}).then(r=>r.json());
    append(res.agent, res.response);
    document.getElementById("upl").style.display = "none";
  }
  
  function append(who, txt){
    const chat = document.getElementById("chat");
    const p = document.createElement("p");
    p.innerHTML = `<b>${who}:</b> ${txt}`;
    chat.appendChild(p);
    chat.scrollTop = chat.scrollHeight;
  }
  