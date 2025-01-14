document.addEventListener('DOMContentLoaded', function() {
    loadSites();
    
    const newSiteForm = document.getElementById('newSiteForm');
    newSiteForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const siteName = document.getElementById('siteName').value;
        const isClient = document.getElementById('isClient').checked;
        
        fetch('/api/sites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: siteName,
                is_client: isClient
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Erro ao cadastrar site: ' + data.error);
            } else {
                loadSites();
                newSiteForm.reset();
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao cadastrar site');
        });
    });
});

function loadSites() {
    fetch('/api/sites')
        .then(response => response.json())
        .then(sites => {
            const sitesList = document.getElementById('sitesList');
            sitesList.innerHTML = '';
            
            if (sites.length === 0) {
                sitesList.innerHTML = '<p class="text-muted">Nenhum site cadastrado</p>';
                return;
            }
            
            const table = document.createElement('table');
            table.className = 'table table-hover';
            
            // Cabeçalho
            const thead = document.createElement('thead');
            thead.innerHTML = `
                <tr>
                    <th>Nome do Site</th>
                    <th>Tipo</th>
                    <th>Ações</th>
                </tr>
            `;
            table.appendChild(thead);
            
            // Corpo da tabela
            const tbody = document.createElement('tbody');
            sites.forEach(site => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${site.name}</td>
                    <td>${site.is_client ? '<span class="badge bg-primary">Cliente</span>' : '<span class="badge bg-secondary">Concorrente</span>'}</td>
                    <td>
                        <a href="/evaluate/${site.id}" class="btn btn-sm btn-primary">Avaliar</a>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            
            table.appendChild(tbody);
            sitesList.appendChild(table);
        })
        .catch(error => {
            console.error('Erro:', error);
            document.getElementById('sitesList').innerHTML = '<p class="text-danger">Erro ao carregar sites</p>';
        });
}
