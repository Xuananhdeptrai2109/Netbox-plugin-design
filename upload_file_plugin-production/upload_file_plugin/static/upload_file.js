
let tempFiles = [];
let uploadedFilesList = [];
let deletedFilesList = [];
let hasFileChanges = false; // Biến để kiểm tra có file thay đổi hay không
let originalFiles = []; // Lưu trữ danh sách file ban đầu từ DB

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Hàm upload file lên server
function uploadFilesToServer(files, objectId = null) {
  const formData = new FormData();

  // Thêm tất cả file vào FormData
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }

  // Thêm thông tin object
  const modelName = document.getElementById('incident-model-name').value;
  const sessionKey = document.getElementById('incident-session-key').value;
  const valid_flg = document.getElementById('validate-flag').value;
  const type_file = document.getElementById('list-type-file').value;
  formData.append('object_id', objectId || '');
  formData.append('model_name', modelName);
  formData.append('session_key', sessionKey);
  formData.append('valid_flg', valid_flg)
  formData.append('type_file', type_file)

  // Gọi API upload
  return fetch(window.UPLOAD_FILE_URL, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie('csrftoken'),
      "X-Requested-With": "XMLHttpRequest"
    },
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.errors && data.errors.length > 0) {
      // Có lỗi xảy ra
      const errorMessage = data.errors.join('\n');
      showCustomToast('Lỗi upload file:\n' + errorMessage, 'danger');
      return { success: false, errors: data.errors };
    } else {
      // Upload thành công
      if (data.saved_files && data.saved_files.length > 0) {
        data.saved_files.forEach(f => {
          if(!checkValidation(f)){
            return { success: false, error: "File is not validate" }
          } 
          uploadedFilesList.push({ file_name: f.file_name, path: f.path, size: f.size });
        });
        
        updateUploadedFilesInput();
      }
      return { success: true, saved_files: data.saved_files };
    }
  })
  .catch(error => {
    console.error('Upload error:', error);
    showCustomToast('Có lỗi xảy ra khi upload file!', 'danger');
    return { success: false, error: error.message };
  });
}

// Render file list từ biến tempFiles và file từ DB
function renderFileList() {
  const list = document.getElementById('incident-upload-list');
  list.innerHTML = '';

  // Hiển thị file từ DB (nếu có)
  var dbFiles = window.UPLOADED_FILES || [];

  // Hiển thị file tạm (từ biến tempFiles) - chỉ hiển thị khi chưa có object_id
  if (!document.getElementById('incident-object-id').value) {
    tempFiles.forEach((file, index) => {
      list.innerHTML += `
        <div class="attachment-item temp-file" data-temp-index="${index}">
          <span class="icon">📄</span>
            <div class="filename">
                  <a href="${file.path}" target="_blank" class="download-link">${file.name}</a>
          </div>
          <div class="filesize">${(file.size/1024).toFixed(1)} KB</div>
          <div class="created">Tạm thời</div>
          <button type="button" class="delete-btn" data-temp-index="${index}" title="Xóa">🗑</button>
        </div>
      `;
    });
  }

  // Hiển thị file từ DB
  dbFiles.forEach(file => {
    list.innerHTML += `
      <div class="attachment-item" data-id="${file.id}">
        <span class="icon">📄</span>
          <div class="filename">
          <a href="/media/${file.file}" target="_blank" class="download-link">${file.file_name}</a>
          </div>
        <div class="filesize">${(file.size/1024).toFixed(1)} KB</div>
        <div class="created">${file.created_at}</div>
        <button type="button" class="delete-btn" data-id="${file.id}" title="Xóa">🗑</button>
      </div>
    `;
  });

  // Gán sự kiện xóa cho các nút
  list.querySelectorAll('.delete-btn').forEach(btn => {
    btn.onclick = function() {
      const fileId = this.getAttribute('data-id');
      const tempIndex = this.getAttribute('data-temp-index');
      const uploadedIndex = this.getAttribute('data-uploaded-index');
      
      if (tempIndex !== null) {
        // Xóa file tạm khỏi biến tempFiles

          tempFiles.splice(parseInt(tempIndex), 1);
          renderFileList();
      } else if (uploadedIndex !== null) {
        // Xóa file vừa upload (chưa lưu DB)
          const idx = parseInt(uploadedIndex);
          if (idx >= 0 && idx < uploadedFilesList.length) {
            // Lưu thông tin file đã xóa vào deletedFilesList
            deletedFilesList.push(uploadedFilesList[idx]);
            // Xóa khỏi mảng uploadedFilesList
            uploadedFilesList.splice(idx, 1);
            updateUploadedFilesInput();
          }
          // Xóa khỏi giao diện
          btn.closest('.attachment-item').remove();
          updateAllFilesInput();
          document.activeElement.blur();
      } else {
        // Xóa file từ DB (chỉ xóa vật lý trên giao diện, không gọi API)

          // Lưu thông tin file đã xóa vào deletedFilesList
          if (window.UPLOADED_FILES) {
            const idx = window.UPLOADED_FILES.findIndex(f => f.id == fileId);
            if (idx !== -1) {
              deletedFilesList.push(window.UPLOADED_FILES[idx]);
              window.UPLOADED_FILES.splice(idx, 1);
            }
          }
          // Xóa khỏi giao diện
          btn.closest('.attachment-item').remove();
          updateAllFilesInput();
          document.activeElement.blur(); // Bỏ focus khỏi input sau khi xóa
        }
      }
  });
}

document.addEventListener('DOMContentLoaded', function() {
  var fileInput = document.getElementById('incident-upload-file-input');
  var resultDiv = document.getElementById('incident-upload-result');
  
  // Lưu danh sách file ban đầu từ DB
  originalFiles = window.UPLOADED_FILES ? [...window.UPLOADED_FILES] : [];
  
  renderFileList();
  updateAllFilesInput();

  // Chọn file - GỌI API NGAY LẬP TỨC
  fileInput.addEventListener('change', function(e) {
    const files = e.target.files;
    if (files.length > 0) {
      const objectId = document.getElementById('incident-object-id').value;

      // Upload ngay lập tức (không reload trang)
      resultDiv.innerHTML = `
        <i class="mdi mdi-loading mdi-spin" style="font-size:20px;color:blue;vertical-align:middle;"></i> Đang upload file...
      `;
      uploadFilesToServer(files, objectId).then(result => {
        console.log('Upload result:', result); // DEBUG
        let html = '';
        if (result.saved_files && result.saved_files.length > 0) {
          const list = document.getElementById('incident-upload-list');
          result.saved_files.forEach((file,index) => {
            valid_extensions = [
                'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff',
                'pdf', 'docx', 'xlsx', 'pptx', 'odt', 'ods',
                'txt', 'csv', 'json', 'yaml', 'xml', 'md', 'log',
                'mp3', 'wav', 'mp4', 'mov', 'avi', 'mkv',
              ]
              if (document.getElementById('list-type-file').value.trim() == '' ){
                type_file_valid = valid_extensions
              }
              else{
              type_file_valid = document.getElementById('list-type-file').value
                .replace('[', '')
                .replace(']', '')
                .split(',')
                .map(s => s.trim().replace(/'/g, '')).join(', ')
              }
            if(checkValidation(file)){
              list.innerHTML += `
              <div class="attachment-item">
                <span class="icon">📄</span>
                <div class="filename">
                  <a href="${getAbsoluteFileUrl(file.path)}" target="_blank" class="download-link">${file.file_name}</a>
                </div>
                <div class="filesize">${(file.size/1024).toFixed(1)} KB</div>
                <div class="created">Vừa upload</div>
                 <button type="button" class="delete-btn" data-uploaded-index="${index}" title="Xóa">🗑</button>
              </div>
            `;
            }
            else{result.errors = ["File được nhập không đúng định dạng", file.file_name , "Các file đúng định dạng là: "
              + type_file_valid]
              }
          })
          
          // Gán lại event listener cho tất cả nút delete sau khi thêm file mới
          list.querySelectorAll('.delete-btn').forEach(btn => {
            btn.onclick = function() {
              const fileId = this.getAttribute('data-id');
              const tempIndex = this.getAttribute('data-temp-index');
              const uploadedIndex = this.getAttribute('data-uploaded-index');
              
              if (tempIndex !== null) {
                // Xóa file tạm khỏi biến tempFiles
                tempFiles.splice(parseInt(tempIndex), 1);
                renderFileList();

              } else if (uploadedIndex !== null) {
                // Xóa file vừa upload (chưa lưu DB)
                  const idx = parseInt(uploadedIndex);
                  if (idx >= 0 && idx < uploadedFilesList.length) {
                    deletedFilesList.push(uploadedFilesList[idx]);
                    uploadedFilesList.splice(idx, 1);
                    updateUploadedFilesInput();
                  
                  // Xóa khỏi giao diện
                  btn.closest('.attachment-item').remove();
                  updateAllFilesInput();
                  document.activeElement.blur();
                }
              } else {
                // Xóa file từ DB (chỉ xóa vật lý trên giao diện, không gọi API)

                  // Lưu thông tin file đã xóa vào deletedFilesList
                  if (window.UPLOADED_FILES) {
                    const idx = window.UPLOADED_FILES.findIndex(f => f.id == fileId);
                    if (idx !== -1) {
                      deletedFilesList.push(window.UPLOADED_FILES[idx]);
                      window.UPLOADED_FILES.splice(idx, 1);
                    }
                  }
                  // Xóa khỏi giao diện
                  btn.closest('.attachment-item').remove();
                  updateAllFilesInput();
                  document.activeElement.blur(); // Bỏ focus khỏi input sau khi xóa
              }
            }
          });
          
          // Cập nhật all-files-input sau khi upload thành công
          updateAllFilesInput();
        }
        if (result.errors && result.errors.length > 0) {
          html += '<br><span style="color:orange;">Một số file lỗi: ' + result.errors.join('<br>') + '</span>';
        }
        if ((!result.saved_files || result.saved_files.length === 0) && result.errors && result.errors.length > 0) {
          html = '<span style="color:red;">Upload file thất bại!<br>' + result.errors.join('<br>') + '</span>';
        }
        // Nếu không có file thành công và không có lỗi, vẫn báo thành công (trường hợp backend trả về success=true)
        if (!html && result.success) {
          showCustomToast('Upload file thành công!', 'success')
        }
        resultDiv.innerHTML = html;
      });
      // Reset input để có thể chọn lại file cùng tên
      fileInput.value = '';
    }
  });



  // Intercept form submit để tự động gửi file tạm
  const incidentForm = document.querySelector('form');
  if (incidentForm) {
    incidentForm.addEventListener('submit', function(e) {
      // Luôn cập nhật input hidden all-files-input với danh sách file đang hiển thị
      updateAllFilesInput();
      
      // Cập nhật trạng thái thay đổi file
      updateFileChangesStatus();
     
      // Chỉ xử lý khi có file tạm và đang tạo mới incident
      if (tempFiles.length > 0 && !document.getElementById('incident-object-id').value) {
        e.preventDefault();

        // Lấy form data hiện tại
        const formData = new FormData(incidentForm);

        // Thêm file tạm vào form data
        tempFiles.forEach((tempFile, index) => {
          formData.append('files', tempFile.file);
        });

        // Thêm danh sách file đã xóa vào form data
        formData.append('deleted_files', JSON.stringify(deletedFilesList));

        // Submit form với file đã được thêm
        fetch(incidentForm.action, {
          method: 'POST',
          body: formData,
          headers: {
            "X-CSRFToken": getCookie('csrftoken')
          }
        })
        .then(response => {
          if (response.redirected) {
            // Nếu có redirect, chuyển hướng
            window.location.href = response.url;
          } else if (response.ok) {
            // Nếu thành công nhưng không redirect, reload trang
            window.location.reload();
          } else {
            // Nếu có lỗi, hiển thị response
            return response.text();
          }
        })
        .then(html => {
          if (html) {
            // Hiển thị response nếu có lỗi
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            document.body.appendChild(tempDiv);
          }
        })
        .catch(error => {
          console.error('Error:', error);
          showCustomToast('Có lỗi xảy ra khi tạo incident!', 'danger');
        });
      } else {
        // Nếu không phải submit tạo mới, vẫn cập nhật input hidden deleted-files-input
        const deletedInput = document.getElementById('deleted-files-input');
        if (deletedInput) {
          deletedInput.value = JSON.stringify(deletedFilesList);
        }
      }
    });
  }
});

// Hàm cập nhật input hidden với danh sách file đã upload
function updateUploadedFilesInput() {
  const input = document.getElementById('uploaded-files-input');
  if (input) {
    input.value = JSON.stringify(uploadedFilesList);
  }
  
  // Cập nhật all-files-input với tất cả file
  updateAllFilesInput();
  
  // Cập nhật trạng thái thay đổi
  updateFileChangesStatus();
}

// Hàm lấy danh sách file hiện tại (sau khi đã xử lý thêm/xóa)
function getCurrentFilesState() {
  // Lấy file từ DB còn lại (sau khi xóa)
  let dbFiles = (window.UPLOADED_FILES || []).filter(file => {
    return !deletedFilesList.some(deletedFile => {
      if (file.id && deletedFile.id) {
        return file.id === deletedFile.id;
      }
      return file.file_name === deletedFile.file_name && file.path === deletedFile.path;
    });
  });

  // Lấy file vừa upload (chưa lưu DB)
  let uploadedFiles = uploadedFilesList.map(f => ({
    file_name: f.file_name,
    path: f.path,
    size: f.size
  }));

  // Lấy file tạm (chưa lưu DB)
  let tempFilesData = tempFiles.map(f => ({
    file_name: f.name,
    path: f.path || ''
  }));


  return [...dbFiles.map(f => ({file_name: f.file_name, path: f.path || f.file})), ...uploadedFiles, ...tempFilesData];
}
function isFilesArrayEqual(arr1, arr2) {
  if (arr1.length !== arr2.length) return false;
  // Sắp xếp để so sánh không phụ thuộc thứ tự
  const sortFn = (a, b) => (a.file_name + a.path).localeCompare(b.file_name + b.path);
  const sorted1 = [...arr1].sort(sortFn);
  const sorted2 = [...arr2].sort(sortFn);
  for (let i = 0; i < sorted1.length; i++) {
    if (sorted1[i].file_name !== sorted2[i].file_name || sorted1[i].path !== sorted2[i].path) {
      return false;
    }
  }
  return true;
}

// Sửa lại hàm updateFileChangesStatus
function updateFileChangesStatus() {
  const currentFiles = getCurrentFilesState();
  const originalFilesSimple = (originalFiles || []).map(f => ({
    file_name: f.file_name || f.name,
    path: f.path || f.file
  }));
  // So sánh
  hasFileChanges = !isFilesArrayEqual(currentFiles, originalFilesSimple);

  // Cập nhật input hidden
  const changesInput = document.getElementById('has-file-changes-input');
  if (changesInput) {
    changesInput.value = hasFileChanges ? 'true' : 'false';
  }
  console.log('File changes status:', hasFileChanges);
}

// Hàm cập nhật input hidden với tất cả file (bao gồm cả uploaded-files)
function updateAllFilesInput() {
  const allFilesInput = document.getElementById('all-files-input');
  if (allFilesInput) {
    const allFiles = getAllDisplayedFiles();
    console.log('Updated all-files-input:', allFiles);
    allFilesInput.value = JSON.stringify(allFiles);
  }
  
  // Cập nhật trạng thái thay đổi
  updateFileChangesStatus();
}


//get tất cả các file đang có trên màn hình và db
function getAllDisplayedFiles() {
  let files = [];
  // File tạm (chỉ khi chưa có object_id)
  if (!document.getElementById('incident-object-id').value) {
    const tempFilesData = tempFiles.map(f => ({
      name: f.name,
      size: f.size,
      path: f.path || ''
    }));
    files = files.concat(tempFilesData);
  }
  
  // File vừa upload (chưa lưu DB) - gộp vào all-files-input
  const uploadedFilesData = uploadedFilesList.map(f => ({
    file_name: f.file_name,
    path: f.path,
    size: f.size
  }));
  files = files.concat(uploadedFilesData);
  // File từ DB
  if (window.UPLOADED_FILES) {
    const dbFilesData = window.UPLOADED_FILES.map(f => ({
      file_name: f.file_name,
      path: f.file,
    }));
    files = files.concat(dbFilesData);
  }
  
  return files;
}

// Hàm lấy giá trị tuyệt đối file 
function getAbsoluteFileUrl(path) {
  if (!path) return '#';
  if (path.startsWith('http') || path.startsWith('/')) return path;
  return '/' + path.replace(/^\/+/, '');
}

const customBox = document.getElementById('custom-upload-box');
const fileInput = document.getElementById('incident-upload-file-input');
customBox.addEventListener('click', function(e) {
  // Chỉ trigger khi click vào box hoặc chữ browse
  if (e.target.classList.contains('upload-browse') || e.target === customBox) {
    fileInput.click();
  }
});
// Optional: highlight box on drag over
customBox.addEventListener('dragover', function(e) {
  e.preventDefault();
  customBox.style.borderColor = '#1976d2';
});
customBox.addEventListener('dragleave', function(e) {
  e.preventDefault();
  customBox.style.borderColor = '#bdbdbd';
});


customBox.addEventListener('drop', function(e) {
  e.preventDefault();
  customBox.style.borderColor = '#bdbdbd';

  const files = e.dataTransfer.files;
  if (files.length > 0) {
    // Hiển thị trạng thái đang upload
    const resultDiv = document.getElementById('incident-upload-result');
    resultDiv.innerHTML = `
      <i class="mdi mdi-loading mdi-spin" style="font-size:20px;color:blue;vertical-align:middle;"></i> Đang upload file...
    `;

    const objectId = document.getElementById('incident-object-id').value;
    uploadFilesToServer(files, objectId).then(result => {
      let html = '';
      if (result.saved_files && result.saved_files.length > 0) {
        const list = document.getElementById('incident-upload-list');
        result.saved_files.forEach((file, index) => {
          list.innerHTML += `
            <div class="attachment-item">
              <span class="icon">📄</span>
              <div class="filename">
                 <a href="${getAbsoluteFileUrl(file.path)}" target="_blank" class="download-link">${file.file_name}</a>
              </div>
              <div class="filesize">${(file.size/1024).toFixed(1)} KB</div>
              <div class="created">Vừa upload</div>
              <button type="button" class="delete-btn" data-uploaded-index="${index}" title="Xóa">🗑</button>
            </div>
          `;
        });
        list.querySelectorAll('.delete-btn').forEach(btn => {
          btn.onclick = function() {
          }
        });
        updateAllFilesInput();
      }
      if (result.errors && result.errors.length > 0) {
        html += '<br><span style="color:orange;">Một số file lỗi: ' + result.errors.join('<br>') + '</span>';
      }
      if ((!result.saved_files || result.saved_files.length === 0) && result.errors && result.errors.length > 0) {
        html = '<span style="color:red;">Upload file thất bại!<br>' + result.errors.join('<br>') + '</span>';
      }
      if (!html && result.success) {
        showCustomToast('Upload file thành công!', 'success')
      }
      resultDiv.innerHTML = html;
    });
  }
});

function checkValidation(file) {
  const validateFlag = document.getElementById('validate-flag').value;
  const typeFile = document.getElementById('list-type-file').value;
  const validateSpan = document.getElementById('validate-file');
  valid_extensions = [
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff',
    '.pdf', '.docx', '.xlsx', '.pptx', '.odt', '.ods',
    '.txt', '.csv', '.json', '.yaml', '.xml', '.md', '.log',
    '.mp3', '.wav', '.mp4', '.mov', '.avi', '.mkv',
  ];
  if(valid_extensions.includes(file.file_name.split('.').pop().toLowerCase())){
    return false
  }
  if(validateFlag && typeFile != null && !typeFile.includes(file.file_name.split('.').pop().toLowerCase())){
    return false
  }
  return true
}


