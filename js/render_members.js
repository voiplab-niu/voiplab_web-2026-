document.addEventListener('DOMContentLoaded', function () {
  const container = document.getElementById('members-container');
  if (!container) return;

  fetch('js/members.json')
    .then(res => res.json())
    .then(data => {
      container.innerHTML = '';
      // Helper to create a grid for a list of people
      function renderSection(title, list) {
        const section = document.createElement('div');
        const h = document.createElement('div');
        h.style.fontSize = '2em';
        h.style.marginBottom = '10px';
        h.innerHTML = '<b>' + title + '</b>';
        section.appendChild(h);

        const table = document.createElement('table');
        table.style.width = '100%';
        table.style.margin = '0 auto';

        // render in rows of 3
        for (let i = 0; i < list.length; i += 3) {
          const trImg = document.createElement('tr');
          const trInfo = document.createElement('tr');
          const trId = document.createElement('tr');

          for (let j = i; j < i + 3; j++) {
            const tdImg = document.createElement('td');
            tdImg.style.width = '30%';
            tdImg.style.textAlign = 'center';
            if (list[j]) {
              const img = document.createElement('img');
              img.src = list[j].image || 'images/boy.jpg';
              img.alt = list[j].name;
              img.width = 303;
              img.height = 303;
              tdImg.appendChild(img);
              const nameDiv = document.createElement('div');
              nameDiv.style.fontSize = '1.2em';
              nameDiv.innerHTML = '<b>' + list[j].name + '</b>';
              tdImg.appendChild(nameDiv);
            }
            trImg.appendChild(tdImg);

            const tdInfo = document.createElement('td');
            tdInfo.style.width = '30%';
            tdInfo.style.textAlign = 'center';
            tdInfo.style.fontSize = '1.2em';
            tdInfo.innerText = (list[j] && list[j].email) ? list[j].email : '';
            trInfo.appendChild(tdInfo);

            const tdId = document.createElement('td');
            tdId.style.width = '30%';
            tdId.style.textAlign = 'center';
            tdId.style.fontSize = '1.2em';
            tdId.innerText = (list[j] && list[j].id) ? list[j].id : '';
            trId.appendChild(tdId);
          }

          table.appendChild(trImg);
          table.appendChild(trInfo);
          table.appendChild(trId);

          // spacer
          const spacer = document.createElement('tr');
          const sTd = document.createElement('td');
          sTd.colSpan = 3;
          sTd.style.height = '20px';
          spacer.appendChild(sTd);
          table.appendChild(spacer);
        }

        section.appendChild(table);
        return section;
      }

      // Current members
      container.appendChild(renderSection('當前成員', data.current_members || []));
      // Project students
      container.appendChild(renderSection('專題生', data.project_students || []));
    })
    .catch(err => {
      const container = document.getElementById('members-container');
      if (container) container.innerText = '載入成員資料失敗';
      console.error('Failed loading members.json', err);
    });
});
