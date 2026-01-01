/**
 * Table Preferences Component
 * 
 * This component initializes DataTables on admin pages with per-user, per-view persistence.
 * 
 * Usage: Mark your table with data-table-view="admin.viewname"
 * The component will auto-load preferences from the server and apply them.
 * 
 * Requires: jQuery, DataTables, DataTables Bootstrap5 theme, ColReorder, Buttons extensions
 */

(function(){
    'use strict';
    
    // Utility: get CSRF token from meta tag or cookie
    function getCsrfToken(){
        var token = document.querySelector('meta[name="csrf-token"]');
        if(token) return token.getAttribute('content');
        var name = 'csrf_token';
        var value = '; ' + document.cookie;
        var parts = value.split('; ' + name + '=');
        if(parts.length == 2) return parts.pop().split(';').shift();
        return '';
    }
    
    // Utility: safe AJAX POST with CSRF using jQuery
    function safeAjaxPost(url, data){
        return new Promise(function(resolve, reject){
            jQuery.ajax({
                url: url,
                type: 'POST',
                contentType: 'application/json',
                headers: { 'X-CSRFToken': getCsrfToken() },
                data: JSON.stringify(data),
                success: function(resp){ resolve(resp); },
                error: function(xhr, status, err){ reject(new Error(status + ': ' + err)); }
            });
        });
    }
    
    // Utility: safe AJAX GET using jQuery
    function safeAjaxGet(url){
        return new Promise(function(resolve, reject){
            jQuery.ajax({
                url: url,
                type: 'GET',
                dataType: 'json',
                success: function(resp){ resolve(resp); },
                error: function(xhr, status, err){ reject(new Error(status + ': ' + err)); }
            });
        });
    }
    
    // Main initialization function
    function initTableFromElement(tableEl){
        if(!tableEl) return;
        
        var viewKey = tableEl.getAttribute('data-table-view');
        if(!viewKey){
            console.warn('[table_prefs] Table missing data-table-view attribute');
            return;
        }
        
        if(tableEl._dtInitialized){
            console.log('[table_prefs] Table already initialized:', viewKey);
            return;
        }
        tableEl._dtInitialized = true;
        
        console.log('[table_prefs] Initializing table:', viewKey);
        
        // Load preferences from server
        safeAjaxGet('/api/user/preferences?view=' + encodeURIComponent(viewKey))
            .then(function(response){
                var savedPrefs = (response && response.preferences) || {};
                
                // Build DataTable initialization options
                var dtOptions = {
                    responsive: true,
                    dom: 'Blfrtip',
                    lengthMenu: [10, 25, 50, 100],
                    pageLength: savedPrefs.pageLength || 10,
                    searching: true,
                    ordering: true,
                    buttons: [
                        'copy',
                        'csv',
                        'excel'
                    ],
                    colReorder: true,
                    stateSave: false,
                    language: {
                        lengthMenu: '_MENU_ registros por página',
                        info: 'Mostrando _START_ a _END_ de _TOTAL_ registros',
                        infoEmpty: 'Nenhum registro disponível',
                        search: 'Filtrar:',
                        zeroRecords: 'Nenhum registro encontrado',
                        paginate: {
                            first: 'Primeira',
                            last: 'Última',
                            next: 'Próxima',
                            previous: 'Anterior'
                        }
                    }
                };
                
                // Apply column order if saved
                if(savedPrefs.columnOrder && Array.isArray(savedPrefs.columnOrder)){
                    dtOptions.colReorder = { order: savedPrefs.columnOrder };
                }
                
                // Apply sorting if saved
                if(savedPrefs.order && Array.isArray(savedPrefs.order)){
                    dtOptions.order = savedPrefs.order;
                }
                
                // Initialize DataTable
                try {
                    var dt = jQuery(tableEl).DataTable(dtOptions);
                    console.log('[table_prefs] DataTable initialized successfully for:', viewKey);
                    
                    // Debounced save function
                    var saveTimeout = null;
                    function schedulePreferenceSave(){
                        clearTimeout(saveTimeout);
                        saveTimeout = setTimeout(function(){
                            savePreferences(dt, viewKey);
                        }, 700);
                    }
                    
                    // Listen for changes: column reorder, sort, page length
                    jQuery(tableEl).on('column-reorder', schedulePreferenceSave);
                    dt.on('order', schedulePreferenceSave);
                    dt.on('length.dt', schedulePreferenceSave);
                    
                } catch(e){
                    console.error('[table_prefs] Failed to initialize DataTable for', viewKey, ':', e);
                }
            })
            .catch(function(err){
                console.error('[table_prefs] Failed to load preferences for', viewKey, ':', err);
                // Still try to initialize DataTable without saved prefs
                try {
                    jQuery(tableEl).DataTable({
                        responsive: true,
                        dom: 'Blfrtip',
                        lengthMenu: [10, 25, 50, 100],
                        buttons: [
                            'copy',
                            'csv',
                            'excel'
                        ],
                        colReorder: true,
                        language: {
                            lengthMenu: '_MENU_ registros por página',
                            info: 'Mostrando _START_ a _END_ de _TOTAL_ registros',
                            infoEmpty: 'Nenhum registro disponível',
                            search: 'Filtrar:',
                            zeroRecords: 'Nenhum registro encontrado',
                            paginate: {
                                first: 'Primeira',
                                last: 'Última',
                                next: 'Próxima',
                                previous: 'Anterior'
                            }
                        }
                    });
                    console.log('[table_prefs] DataTable initialized (without saved prefs) for:', viewKey);
                } catch(e2){
                    console.error('[table_prefs] DataTable initialization failed:', e2);
                }
            });
    }
    
    // Save preferences to server
    function savePreferences(dt, viewKey){
        var data = {
            pageLength: dt.page.len(),
            order: dt.order(),
            columnOrder: []
        };
        
        // Get column order from ColReorder if available
        try {
            var cr = dt.colReorder;
            if(cr && cr.order && typeof cr.order === 'function'){
                data.columnOrder = cr.order();
            }
        } catch(e) {
            // ColReorder not available or error, skip column order
        }
        
        safeAjaxPost('/api/user/preferences', {
            view_key: viewKey,
            preferences: data
        }).then(function(){
            console.log('[table_prefs] Preferences saved for:', viewKey);
        }).catch(function(err){
            console.warn('[table_prefs] Failed to save preferences for', viewKey, ':', err);
        });
    }
    
    // Reset preferences: clear saved data and reload table
    function resetTablePreferences(viewKey){
        if(!viewKey) return;
        safeAjaxPost('/api/user/preferences', {
            view_key: viewKey,
            preferences: null
        }).then(function(){
            console.log('[table_prefs] Preferences reset for:', viewKey);
            // Reload page to show default state
            location.reload();
        }).catch(function(err){
            console.error('[table_prefs] Failed to reset preferences for', viewKey, ':', err);
        });
    }
    
    // Public API
    window.initAdminTable = function(tableEl){
        if(!tableEl) {
            tableEl = document.querySelector('table[data-table-view]');
        }
        if(tableEl) initTableFromElement(tableEl);
    };
    
    window.initAdminTables = function(){
        console.log('[table_prefs] initAdminTables() called');
        var tables = document.querySelectorAll('table[data-table-view]');
        console.log('[table_prefs] Found', tables.length, 'tables to initialize');
        tables.forEach(function(table){
            console.log('[table_prefs] Processing table:', table.getAttribute('data-table-view'));
            initTableFromElement(table);
        });
        console.log('[table_prefs] All tables processed');
    };
    
    window.resetAdminTablePreferences = function(viewKey){
        resetTablePreferences(viewKey);
    };
    
    // Initialize reset button listeners
    document.addEventListener('DOMContentLoaded', function(){
        document.querySelectorAll('[data-reset-view]').forEach(function(btn){
            btn.addEventListener('click', function(){
                var viewKey = this.getAttribute('data-reset-view');
                if(confirm('Limpar preferências da tabela? A página será recarregada.')){
                    resetTablePreferences(viewKey);
                }
            });
        });
    });
    
})();