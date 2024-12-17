document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("noteModal");
    const closeBtn = document.getElementById("closeModal");
    const modalContent = document.getElementById("modalContent");

    document.querySelectorAll(".note-link").forEach(link => {
        link.addEventListener("click", async (event) => {
            event.preventDefault();
            const noteId = event.target.getAttribute("data-id");

            // メモ詳細を取得
            const response = await fetch(`/note_detail/${noteId}`);
            const noteDetail = await response.json();

            // ポップアップ内容を更新
            modalContent.innerHTML = `
                <h2>${noteDetail.title}</h2>
                <p><strong>カテゴリ:</strong> ${noteDetail.category}</p>
                <p><strong>作成日:</strong> ${noteDetail.created_at}</p>
                <p>${noteDetail.content}</p>
                <button onclick="window.location.href='/edit_note/${noteDetail.id}'">編集</button>
                <button onclick="window.location.href='/delete_note/${noteDetail.id}'">削除</button>
            `;
            modal.style.display = "block";
        });
    });

    // モーダルを閉じる
    closeBtn.addEventListener("click", () => {
        modal.style.display = "none";
    });
});

// 編集ポップアップを開く
function openEditPopup(id, title, content, category) {
    document.getElementById('editTitle').value = title;
    document.getElementById('editContent').value = content;
    document.getElementById('editCategory').value = category;
    document.getElementById('editNoteId').value = id;

    document.getElementById('editPopup').style.display = 'block';
}

// 編集ポップアップを閉じる
function closeEditPopup() {
    document.getElementById('editPopup').style.display = 'none';
}
