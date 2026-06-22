# Edu Assistant

Portal acadêmico com interface React, API FastAPI, integração Moodle REST e
fallback Streamlit.

## Apresentação

Com o Moodle ativo em `http://localhost:8080`, execute:

```powershell
.\scripts\Start-EduAssistant.ps1
```

Acesse `http://localhost:8000`.

O dashboard mostra automaticamente o status da integração Moodle: conexão,
token REST, usuário identificado, quantidade de cursos matriculados e última
sincronização. Use `Verificar Moodle` para repetir o diagnóstico e
`Sincronizar Moodle` para importar cursos e prazos.

## Desenvolvimento

```powershell
.\scripts\Start-EduAssistantDev.ps1
```

Frontend Vite com hot reload: `http://localhost:5173`

API FastAPI: `http://localhost:8000`

No modo desenvolvimento, alterações no React aparecem com hot reload na porta
`5173`. A porta `8000` fica para a API; se você abrir a raiz dela no modo dev,
ela redireciona para o Vite.

Para encerrar processos iniciados pelos scripts:

```powershell
.\scripts\Stop-EduAssistant.ps1
```

## Fallback Streamlit

```powershell
.\venv\Scripts\python.exe -m streamlit run app.py
```

Acesse `http://localhost:8501`.
