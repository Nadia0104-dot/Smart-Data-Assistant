document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("fileInput");
  const uploadForm = document.getElementById("uploadForm");
  const healthDiv = document.getElementById("healthReport");
  const rowsEl = document.getElementById("rows");
  const colsEl = document.getElementById("cols");
  const duplicatesEl = document.getElementById("duplicates");
  const missingEl = document.getElementById("missing");
  const previewDiv = document.getElementById("previewTable");
  const messageEl = document.getElementById("uploadMessage");
  const progressContainer = document.getElementById("progressContainer");
  const progressBar = document.getElementById("progressBar");
  const dragLabel = document.querySelector("label[for='fileInput']");

  function escapeHtml(s){ 
    return s ? s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;") : ""; 
  }
  function animateNumber(el, endVal, duration=800){
    let startVal=0, range=endVal-startVal, startTime=null;
    function step(timestamp){
      if(!startTime) startTime=timestamp;
      const progress=Math.min((timestamp-startTime)/duration,1);
      el.innerText=Math.floor(progress*range + startVal);
      if(progress<1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}
  // Drag & Drop highlight
  dragLabel.addEventListener("dragover", e=>{
    e.preventDefault();
    dragLabel.style.background="rgba(37,99,235,0.1)";
  });
  dragLabel.addEventListener("dragleave", e=>{
    e.preventDefault();
    dragLabel.style.background="";
  });
  dragLabel.addEventListener("drop", e=>{
    e.preventDefault();
    dragLabel.style.background="";
    fileInput.files=e.dataTransfer.files;
  });

  function renderPreview(data){
    if(!data||!data.length){ 
      previewDiv.innerHTML="<p class='text-gray-600 text-center py-4'>No preview available</p>"; 
      previewDiv.classList.remove("hidden"); 
      return; 
    }
    let html="<table><thead><tr>";
    Object.keys(data[0]).forEach(col=>{ if(col!="_is_duplicate") html+=`<th>${escapeHtml(col)}</th>`; });
    html+="</tr></thead><tbody>";
    data.forEach(row=>{
      const dupClass=row._is_duplicate?"row-duplicate":"";
      html+=`<tr class="${dupClass}">`;
      Object.keys(row).forEach(col=>{
        if(col==="_is_duplicate") return;
        const val=row[col]??"";
        const cellClass=val===""?"cell-missing":"";
        html+=`<td class="${cellClass}">${escapeHtml(String(val))}</td>`;
      });
      html+="</tr>";
    });
    html+="</tbody></table>";
    previewDiv.innerHTML=html;
    previewDiv.classList.remove("hidden");
  }

  uploadForm.addEventListener("submit", async(e)=>{
    e.preventDefault();
    if(!fileInput.files.length) return alert("Please select a file!");
    const formData=new FormData();
    formData.append("file",fileInput.files[0]);

    messageEl.classList.add("hidden");
    progressContainer.classList.remove("hidden");
    progressBar.style.width="0%";

    try{
      const res=await axios.post("/upload", formData,{
        headers:{"Content-Type":"multipart/form-data"},
        onUploadProgress:(pe)=>{
          const percent=Math.round((pe.loaded*100)/pe.total);
          progressBar.style.width=percent+"%";
        }
      });

      const data=res.data;
      rowsEl.innerText=data.health.rows??0;
      colsEl.innerText=data.health.columns??0;
      duplicatesEl.innerText=data.health.duplicates??0;
      missingEl.innerText=(data.health.missing_percent??0)+"%";
      healthDiv.classList.remove("hidden");
      renderPreview(data.preview);

      messageEl.innerText=`Upload successful: ${data.filename}`;
      messageEl.classList.remove("hidden");
      messageEl.classList.remove("text-red-600");
      messageEl.classList.add("text-green-400");

    }catch(err){
      console.error(err);
      messageEl.innerText=err.response?.data?.error||"Upload failed!";
      messageEl.classList.remove("hidden");
      messageEl.classList.add("text-red-600");
    }finally{
      progressContainer.classList.add("hidden");
    }
  });
});