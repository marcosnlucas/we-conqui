// Funções globais
window.addCompetitor = function() {
    const template = document.getElementById('competitorTemplate');
    const clone = template.content.cloneNode(true);
    document.getElementById('competitorsList').appendChild(clone);
}

window.removeCompetitor = function(button) {
    button.closest('.competitor-item').remove();
}

function loadProjects() {
    fetch('/api/projects')
        .then(response => response.json())
        .then(projects => {
            const container = document.getElementById('projectsList');
            
            if (projects.length === 0) {
                container.innerHTML = '<p class="text-muted">Nenhum projeto cadastrado</p>';
                return;
            }
            
            container.innerHTML = projects.map(project => `
                <div class="card mb-3">
                    <div class="card-body">
                        <h5 class="card-title">${project.name}</h5>
                        <p class="card-text">
                            <strong>Site do Cliente:</strong> 
                            <a href="${project.client_site_url}" target="_blank">${project.client_site_name}</a>
                        </p>
                        <p class="card-text">
                            <small class="text-muted">
                                ${project.competitor_count} concorrente(s) | 
                                Criado em ${new Date(project.created_at).toLocaleString()}
                            </small>
                        </p>
                        <div class="btn-group">
                            <a href="/project/${project.id}/pillars" class="btn btn-outline-primary">
                                Gerenciar Pilares
                            </a>
                            <a href="/project/${project.id}/questions" class="btn btn-outline-primary">
                                Gerenciar Perguntas
                            </a>
                            <a href="/project/${project.id}" class="btn btn-outline-success">
                                Avaliar Sites
                            </a>
                        </div>
                    </div>
                </div>
            `).join('');
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao carregar projetos');
        });
}

// Inicialização quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    loadProjects();
    
    document.getElementById('projectForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const competitors = [];
        document.querySelectorAll('.competitor-item').forEach(item => {
            competitors.push({
                name: item.querySelector('.competitor-name').value,
                url: item.querySelector('.competitor-url').value
            });
        });
        
        const projectData = {
            name: document.getElementById('projectName').value,
            client_site_name: document.getElementById('clientSiteName').value,
            client_site_url: document.getElementById('clientSiteUrl').value,
            competitors: competitors
        };
        
        fetch('/api/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(projectData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Erro ao criar projeto: ' + data.error);
            } else {
                loadProjects();
                document.getElementById('projectForm').reset();
                document.getElementById('competitorsList').innerHTML = '';
                bootstrap.Collapse.getInstance(document.getElementById('newProjectForm')).hide();
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao criar projeto');
        });
    });
});
