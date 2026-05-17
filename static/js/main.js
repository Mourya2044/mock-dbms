document.addEventListener('DOMContentLoaded', () => {
    // --- CodeMirror Editor Setup ---
    const editorElement = document.getElementById('sql-editor');
    const editor = CodeMirror.fromTextArea(editorElement, {
        mode: 'text/x-sql',
        theme: 'material-darker',
        lineNumbers: true,
        indentWithTabs: false,
        smartIndent: true,
        lineWrapping: true,
        matchBrackets: true,
        autofocus: true,
        extraKeys: {
            "Ctrl-Enter": () => runQuery()
        }
    });

    // Default editor content
    editor.setValue(`-- Welcome to Mock DBMS Playground
-- Practice Oracle SQL & PL/SQL queries

SELECT empno, ename, job, sal, deptno 
FROM emp 
WHERE sal > 1500 
ORDER BY sal DESC;`);

    // --- State Variables ---
    let currentMode = 'auto';

    // --- DOM Elements ---
    const modeSelect = document.getElementById('exec-mode');
    const btnRun = document.getElementById('btn-run');
    const btnClear = document.getElementById('btn-clear');
    const btnFormat = document.getElementById('btn-format');
    const btnRefreshSchema = document.getElementById('btn-refresh-schema');
    const btnAi = document.getElementById('btn-ai');
    const inputAi = document.getElementById('ai-prompt');

    const metaTime = document.getElementById('meta-time');
    const metaStatus = document.getElementById('meta-status');
    const countRows = document.getElementById('count-rows');
    const countDbms = document.getElementById('count-dbms');

    const tableHead = document.getElementById('table-head');
    const tableBody = document.getElementById('table-body');
    const dbmsConsole = document.getElementById('dbms-console');
    const logConsole = document.getElementById('log-console');

    // --- Event Listeners ---
    modeSelect.addEventListener('change', (e) => { currentMode = e.target.value; });
    btnRun.addEventListener('click', runQuery);
    btnClear.addEventListener('click', () => { editor.setValue(''); editor.focus(); });
    btnFormat.addEventListener('click', formatQuery);
    btnRefreshSchema.addEventListener('click', loadSchema);
    
    btnAi.addEventListener('click', askAi);
    inputAi.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') askAi();
    });

    // Sidebar Tab Switching
    document.querySelectorAll('.sidebar-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.sidebar-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.sidebar-panels .panel').forEach(p => p.classList.remove('active'));
            
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            document.getElementById(targetId).classList.add('active');
        });
    });

    // Results Tab Switching
    document.querySelectorAll('.results-tabs .res-tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            switchResultTab(btn.getAttribute('data-restab'));
        });
    });

    function switchResultTab(targetId) {
        document.querySelectorAll('.results-tabs .res-tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.results-panels .res-panel').forEach(p => p.classList.remove('active'));
        
        const activeBtn = document.querySelector(`.results-tabs .res-tab-btn[data-restab="${targetId}"]`);
        if (activeBtn) activeBtn.classList.add('active');
        const activePanel = document.getElementById(targetId);
        if (activePanel) activePanel.classList.add('active');
    }

    // --- API Interactions ---

    async function loadSchema() {
        try {
            const res = await fetch('/api/schema');
            const data = await res.json();
            if (data.status === 'success') {
                renderSchema(data.schema);
            }
        } catch (e) {
            console.error('Failed to load schema:', e);
        }
    }

    async function loadSnippets() {
        try {
            const res = await fetch('/api/snippets');
            const data = await res.json();
            if (data.status === 'success') {
                renderSnippets(data.snippets);
            }
        } catch (e) {
            console.error('Failed to load snippets:', e);
        }
    }

    async function runQuery() {
        const code = editor.getValue().trim();
        if (!code) {
            updateStatus('Error', 'error');
            logMessage('No code to execute.');
            return;
        }

        updateStatus('Running...', 'ready');
        metaTime.textContent = 'Time: 0 ms';

        try {
            const res = await fetch('/api/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, mode: currentMode })
            });

            const data = await res.json();
            metaTime.textContent = `Time: ${data.execution_time_ms || 0} ms`;

            if (data.status === 'success') {
                updateStatus('Success', 'success');
                logMessage(`[SUCCESS] ${data.message}`);

                if (data.type === 'sql') {
                    renderTable(data.columns || [], data.rows || []);
                    countRows.textContent = (data.rows || []).length;
                    switchResultTab('query-results-tab');
                } else if (data.type === 'plsql') {
                    renderDbmsOutput(data.dbms_output || []);
                    countDbms.textContent = (data.dbms_output || []).length;
                    switchResultTab('dbms-output-tab');
                }
                // Reload schema in case DDL was executed
                loadSchema();
            } else {
                updateStatus('Error', 'error');
                logMessage(`[ERROR] ${data.message}`);
                switchResultTab('log-tab');
            }
        } catch (e) {
            updateStatus('Error', 'error');
            logMessage(`[ERROR] Network or server error: ${e.message}`);
            switchResultTab('log-tab');
        }
    }

    async function askAi() {
        const prompt = inputAi.value.trim();
        if (!prompt) return;

        btnAi.disabled = true;
        btnAi.textContent = 'Generating...';
        updateStatus('Generating SQL...', 'ready');

        try {
            const res = await fetch('/api/ai', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });

            const data = await res.json();

            if (data.status === 'success') {
                const generatedSql = data.sql;
                
                // Set editor content to generated SQL
                editor.setValue(`-- AI Generated from: "${prompt}"\n\n${generatedSql}`);
                inputAi.value = ''; // clear input
                
                logMessage('[AI] Successfully generated SQL.');
                
                // Automatically run the query
                runQuery();
            } else {
                updateStatus('AI Error', 'error');
                logMessage(`[AI ERROR] ${data.message}`);
                switchResultTab('log-tab');
            }
        } catch (e) {
            updateStatus('AI Error', 'error');
            logMessage(`[AI ERROR] Network or server error: ${e.message}`);
            switchResultTab('log-tab');
        } finally {
            btnAi.disabled = false;
            btnAi.textContent = 'Ask AI';
        }
    }

    // --- Render Functions ---

    function renderSchema(schema) {
        const container = document.getElementById('schema-accordion');
        container.innerHTML = '';

        for (const [tableName, tableInfo] of Object.entries(schema)) {
            const item = document.createElement('div');
            item.className = 'accordion-item';

            const header = document.createElement('div');
            header.className = 'accordion-header';
            header.innerHTML = `<span>${tableName}</span><div><button class="btn-view-data" title="View all rows in Results tab">🔍 View Data</button> <span style="margin-left:8px;">${tableInfo.columns.length} cols</span></div>`;

            const btnView = header.querySelector('.btn-view-data');
            btnView.addEventListener('click', (e) => {
                e.stopPropagation();
                const colNames = tableInfo.columns.map(c => c.name);
                renderTable(colNames, tableInfo.sample_data || []);
                countRows.textContent = (tableInfo.sample_data || []).length;
                switchResultTab('query-results-tab');
                logMessage(`[VIEW DATA] Displaying live rows for table ${tableName}.`);
            });

            const body = document.createElement('div');
            body.className = 'accordion-body';

            const colList = document.createElement('ul');
            colList.className = 'schema-cols';

            tableInfo.columns.forEach(col => {
                const li = document.createElement('li');
                li.innerHTML = `<span>${col.name} ${col.pk ? '<span class="col-pk">(PK)</span>' : ''}</span><span class="col-type">${col.type}</span>`;
                colList.appendChild(li);
            });

            body.appendChild(colList);

            // Mini Preview Table
            if (tableInfo.sample_data && tableInfo.sample_data.length > 0) {
                const previewTitle = document.createElement('div');
                previewTitle.className = 'preview-header';
                previewTitle.textContent = `Live Data Preview (${tableInfo.sample_data.length} rows)`;
                body.appendChild(previewTitle);

                const previewTable = document.createElement('table');
                previewTable.className = 'schema-preview-table';
                
                const thead = document.createElement('thead');
                const trHead = document.createElement('tr');
                tableInfo.columns.forEach(col => {
                    const th = document.createElement('th');
                    th.textContent = col.name;
                    trHead.appendChild(th);
                });
                thead.appendChild(trHead);
                previewTable.appendChild(thead);

                const tbody = document.createElement('tbody');
                tableInfo.sample_data.forEach(row => {
                    const tr = document.createElement('tr');
                    row.forEach(val => {
                        const td = document.createElement('td');
                        td.textContent = val === null ? 'NULL' : val;
                        tr.appendChild(td);
                    });
                    tbody.appendChild(tr);
                });
                previewTable.appendChild(tbody);
                body.appendChild(previewTable);
            }

            item.appendChild(header);
            item.appendChild(body);

            header.addEventListener('click', () => {
                item.classList.toggle('active');
            });

            container.appendChild(item);
        }
    }

    function renderSnippets(snippets) {
        const list = document.getElementById('snippets-list');
        list.innerHTML = '';

        snippets.forEach(snip => {
            const li = document.createElement('li');
            li.innerHTML = `<span class="snippet-title">${snip.title}</span><span class="snippet-cat">${snip.category}</span>`;
            li.addEventListener('click', () => {
                editor.setValue(snip.code);
                editor.focus();
            });
            list.appendChild(li);
        });
    }

    function renderTable(columns, rows) {
        tableHead.innerHTML = '';
        tableBody.innerHTML = '';

        if (columns.length === 0) {
            tableHead.innerHTML = '<th>Statement executed successfully. No tabular data.</th>';
            return;
        }

        const headRow = document.createElement('tr');
        columns.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            headRow.appendChild(th);
        });
        tableHead.appendChild(headRow);

        rows.forEach(row => {
            const tr = document.createElement('tr');
            row.forEach(val => {
                const td = document.createElement('td');
                td.textContent = val === null ? 'NULL' : val;
                tr.appendChild(td);
            });
            tableBody.appendChild(tr);
        });
    }

    function renderDbmsOutput(lines) {
        if (lines.length === 0) {
            dbmsConsole.textContent = 'Statement executed successfully. No DBMS_OUTPUT lines.';
            return;
        }
        dbmsConsole.textContent = lines.join('\n');
    }

    function logMessage(msg) {
        const timestamp = new Date().toLocaleTimeString();
        logConsole.textContent = `[${timestamp}] ${msg}\n` + logConsole.textContent;
    }

    function updateStatus(text, type) {
        metaStatus.textContent = text;
        metaStatus.className = `status-badge ${type}`;
    }

    function formatQuery() {
        // Basic uppercase keywords formatting
        let code = editor.getValue();
        const keywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'DECLARE', 'BEGIN', 'END', 'EXCEPTION', 'WHEN', 'THEN', 'IF', 'ELSIF', 'ELSE', 'LOOP', 'FOR', 'WHILE', 'CURSOR', 'IS', 'OPEN', 'FETCH', 'CLOSE', 'COMMIT', 'ROLLBACK', 'ORDER BY', 'GROUP BY', 'HAVING'];
        
        keywords.forEach(kw => {
            const regex = new RegExp(`\\b${kw}\\b`, 'gi');
            code = code.replace(regex, kw);
        });

        editor.setValue(code);
        logMessage('[FORMAT] Query keywords capitalized.');
    }

    // --- Initial Load ---
    loadSchema();
    loadSnippets();
});
