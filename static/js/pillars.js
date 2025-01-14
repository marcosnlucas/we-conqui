document.addEventListener('DOMContentLoaded', function() {
    // Get project_id from URL path
    const pathParts = window.location.pathname.split('/');
    const projectId = pathParts[pathParts.indexOf('project') + 1];
    
    if (!projectId) {
        alert('Erro: ID do projeto não encontrado');
        return;
    }

    loadPillars();
    
    // Formulário de novo pilar
    document.getElementById('pillarForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const pillarData = {
            name: document.getElementById('pillarName').value,
            description: document.getElementById('pillarDescription').value,
            weight: parseInt(document.getElementById('pillarWeight').value),
            project_id: parseInt(projectId)
        };

        fetch('/api/pillars', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(pillarData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Erro ao cadastrar pilar: ' + data.error);
            } else {
                loadPillars();
                document.getElementById('pillarForm').reset();
                bootstrap.Collapse.getInstance(document.getElementById('newPillarForm')).hide();
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao cadastrar pilar');
        });
    });

    // Salvar edição
    document.getElementById('btnSaveEdit').addEventListener('click', function() {
        const pillarId = document.getElementById('editPillarId').value;
        const pillarData = {
            name: document.getElementById('editPillarName').value,
            description: document.getElementById('editPillarDescription').value,
            weight: parseInt(document.getElementById('editPillarWeight').value),
            project_id: parseInt(projectId)
        };

        fetch(`/api/pillars/${pillarId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(pillarData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Erro ao atualizar pilar: ' + data.error);
            } else {
                loadPillars();
                bootstrap.Modal.getInstance(document.getElementById('editPillarModal')).hide();
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao atualizar pilar');
        });
    });

    // Excluir pilar
    document.getElementById('btnDeletePillar').addEventListener('click', function() {
        const pillarId = document.getElementById('editPillarId').value;
        
        // Verificar se existem perguntas associadas
        fetch(`/api/pillars/${pillarId}/questions`)
        .then(response => response.json())
        .then(data => {
            if (data.length > 0) {
                if (!confirm(`Este pilar possui ${data.length} pergunta(s) associada(s). Deseja realmente excluir?`)) {
                    return;
                }
            }
            
            fetch(`/api/pillars/${pillarId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Erro ao excluir pilar: ' + data.error);
                } else {
                    loadPillars();
                    bootstrap.Modal.getInstance(document.getElementById('editPillarModal')).hide();
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Erro ao excluir pilar');
            });
        });
    });
});

function loadPillars() {
    const projectId = window.location.pathname.split('/')[window.location.pathname.split('/').indexOf('project') + 1];
    
    fetch(`/api/projects/${projectId}/pillars`)
        .then(response => response.json())
        .then(pillars => {
            renderPillarsList(pillars);
            renderWeightDistribution(pillars);
        })
        .catch(error => {
            console.error('Erro ao carregar pilares:', error);
            alert('Erro ao carregar pilares');
        });
}

function renderPillarsList(pillars) {
    const container = document.getElementById('pillarsList');
    
    if (pillars.length === 0) {
        container.innerHTML = '<p class="text-muted">Nenhum pilar cadastrado</p>';
        return;
    }
    
    const table = document.createElement('table');
    table.className = 'table table-hover';
    
    table.innerHTML = `
        <thead>
            <tr>
                <th>Nome</th>
                <th>Descrição</th>
                <th>Peso</th>
                <th>Porcentagem</th>
                <th>Perguntas</th>
                <th>Ações</th>
            </tr>
        </thead>
        <tbody>
            ${pillars.map(pillar => `
                <tr>
                    <td>${pillar.name}</td>
                    <td>${pillar.description || '-'}</td>
                    <td>${pillar.weight}/10</td>
                    <td>${pillar.weight_percentage}%</td>
                    <td>${pillar.questions_count || 0}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="editPillar(${pillar.id})">
                            Editar
                        </button>
                    </td>
                </tr>
            `).join('')}
        </tbody>
    `;
    
    container.innerHTML = '';
    container.appendChild(table);
}

function renderWeightDistribution(pillars) {
    const progress = document.querySelector('.progress');
    progress.innerHTML = '';
    
    pillars.forEach((pillar, index) => {
        const bar = document.createElement('div');
        bar.className = `progress-bar ${getProgressBarColor(index)}`;
        bar.style.width = `${pillar.weight_percentage}%`;
        bar.setAttribute('title', `${pillar.name}: ${pillar.weight_percentage}%`);
        bar.textContent = `${pillar.weight_percentage}%`;
        progress.appendChild(bar);
    });
}

function getProgressBarColor(index) {
    const colors = [
        'bg-primary',
        'bg-success',
        'bg-info',
        'bg-warning',
        'bg-danger'
    ];
    return colors[index % colors.length];
}

function editPillar(pillarId) {
    fetch(`/api/pillars/${pillarId}`)
        .then(response => response.json())
        .then(pillar => {
            document.getElementById('editPillarId').value = pillar.id;
            document.getElementById('editPillarName').value = pillar.name;
            document.getElementById('editPillarDescription').value = pillar.description || '';
            document.getElementById('editPillarWeight').value = pillar.weight;
            
            new bootstrap.Modal(document.getElementById('editPillarModal')).show();
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao carregar dados do pilar');
        });
}
