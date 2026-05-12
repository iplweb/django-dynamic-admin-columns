/*
 * django-dynamic-admin-columns — column picker UI.
 *
 * Vanilla JS, no external libraries. Native HTML5 drag-and-drop for
 * desktop. The picker writes to the admin's
 * dynamic-columns/save/ endpoint via JSON POST, then reloads.
 *
 * Two scopes are supported: ``personal`` (default, available to every
 * staff user) and ``global`` (visible only to superusers via the
 * radio group). Saving in ``global`` mode rewrites the ``user IS
 * NULL`` row that every user without a personal layout falls back to.
 */
(function () {
    "use strict";

    function getCookie(name) {
        var cookies = document.cookie ? document.cookie.split("; ") : [];
        for (var i = 0; i < cookies.length; i += 1) {
            var parts = cookies[i].split("=");
            if (parts.shift() === name) {
                return decodeURIComponent(parts.join("="));
            }
        }
        return null;
    }

    function getCsrfToken() {
        // Why: ``CSRF_COOKIE_HTTPONLY = True`` is a recommended hardening
        // (Django security docs) but hides the cookie from JavaScript.
        // Prefer the server-rendered ``{% csrf_token %}`` input we embed
        // in the modal, fall back to the cookie for projects that don't.
        var modal = document.getElementById("dyncol-modal");
        var input =
            (modal && modal.querySelector("input[name='csrfmiddlewaretoken']")) ||
            document.querySelector("input[name='csrfmiddlewaretoken']");
        if (input && input.value) return input.value;
        return getCookie("csrftoken") || "";
    }

    function ready(fn) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", fn);
        } else {
            fn();
        }
    }

    function readPayload(elementId) {
        var el = document.getElementById(elementId);
        if (!el) return [];
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            return [];
        }
    }

    function clearList(list) {
        // Clear children safely without innerHTML; XSS-free.
        while (list.firstChild) {
            list.removeChild(list.firstChild);
        }
    }

    function renderList(list, columns) {
        clearList(list);

        if (!columns.length) {
            var empty = document.createElement("li");
            empty.className = "dyncol-empty";
            empty.textContent = list.dataset.emptyLabel || "";
            list.appendChild(empty);
            return;
        }

        columns.forEach(function (col) {
            var item = document.createElement("li");
            item.className = "dyncol-item";
            item.dataset.colName = col.col_name;
            item.draggable = true;

            var handle = document.createElement("span");
            handle.className = "dyncol-handle";
            handle.setAttribute("aria-hidden", "true");
            handle.textContent = "⋮⋮";
            item.appendChild(handle);

            var label = document.createElement("label");
            label.className = "dyncol-label";

            var checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.className = "dyncol-enabled";
            checkbox.checked = !!col.enabled;
            label.appendChild(checkbox);

            var nameSpan = document.createElement("span");
            nameSpan.textContent = col.verbose_name;
            label.appendChild(nameSpan);

            if (col.verbose_name !== col.col_name) {
                var code = document.createElement("code");
                code.className = "dyncol-colname";
                code.textContent = col.col_name;
                label.appendChild(code);
            }

            item.appendChild(label);
            list.appendChild(item);
        });

        attachDragHandlers(list);
    }

    function attachDragHandlers(list) {
        var dragged = null;

        function clearDropTargets() {
            list.querySelectorAll(".dyncol-drop-target").forEach(function (el) {
                el.classList.remove("dyncol-drop-target");
            });
        }

        // Auto-scroll the list when the dragged pointer approaches its
        // top or bottom edge. ``dragover`` from the child items bubbles
        // up to the list, so this fires throughout the drag without
        // having to bind on every item. Attached once per list element —
        // ``attachDragHandlers`` runs on every re-render (scope toggle),
        // so the ``_dyncolScrollBound`` flag prevents listener leaks.
        if (!list._dyncolScrollBound) {
            list._dyncolScrollBound = true;
            var SCROLL_ZONE = 40; // px — distance from edge that triggers scroll
            var SCROLL_STEP = 14; // px per dragover tick
            list.addEventListener("dragover", function (event) {
                var rect = list.getBoundingClientRect();
                var y = event.clientY;
                if (y < rect.top + SCROLL_ZONE) {
                    list.scrollTop -= SCROLL_STEP;
                } else if (y > rect.bottom - SCROLL_ZONE) {
                    list.scrollTop += SCROLL_STEP;
                }
            });
        }

        list.querySelectorAll(".dyncol-item").forEach(function (item) {
            item.addEventListener("dragstart", function (event) {
                dragged = item;
                item.classList.add("dyncol-dragging");
                if (event.dataTransfer) {
                    event.dataTransfer.effectAllowed = "move";
                    event.dataTransfer.setData(
                        "text/plain",
                        item.dataset.colName || "",
                    );
                }
            });

            item.addEventListener("dragend", function () {
                if (dragged) {
                    dragged.classList.remove("dyncol-dragging");
                }
                clearDropTargets();
                dragged = null;
            });

            item.addEventListener("dragover", function (event) {
                if (!dragged || dragged === item) return;
                event.preventDefault();
                if (event.dataTransfer) {
                    event.dataTransfer.dropEffect = "move";
                }
                clearDropTargets();
                item.classList.add("dyncol-drop-target");
            });

            item.addEventListener("dragleave", function () {
                item.classList.remove("dyncol-drop-target");
            });

            item.addEventListener("drop", function (event) {
                event.preventDefault();
                if (!dragged || dragged === item) return;
                var rect = item.getBoundingClientRect();
                var midpoint = rect.top + rect.height / 2;
                if (event.clientY < midpoint) {
                    list.insertBefore(dragged, item);
                } else {
                    list.insertBefore(dragged, item.nextSibling);
                }
                clearDropTargets();
            });
        });
    }

    function collectPayload(list) {
        var items = list.querySelectorAll(".dyncol-item");
        var columns = [];
        items.forEach(function (item, index) {
            var checkbox = item.querySelector(".dyncol-enabled");
            columns.push({
                col_name: item.dataset.colName,
                enabled: checkbox ? checkbox.checked : false,
                ordering: index + 1,
            });
        });
        return columns;
    }

    function postJson(url, payload) {
        return fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify(payload || {}),
        });
    }

    var activeModal = null;
    function escapeListener(event) {
        if (event.key === "Escape" && activeModal) {
            activeModal.hidden = true;
            document.removeEventListener("keydown", escapeListener);
        }
    }

    function openModal(modal) {
        modal.hidden = false;
        var first = modal.querySelector(".dyncol-item, .dyncol-btn-save");
        if (first) first.focus();
        document.addEventListener("keydown", escapeListener);
    }

    function closeModal(modal) {
        modal.hidden = true;
        document.removeEventListener("keydown", escapeListener);
    }

    function currentScope(modal) {
        var checked = modal.querySelector(
            "input[name='dyncol-scope']:checked",
        );
        return checked ? checked.value : "personal";
    }

    // Server-rendered translations live in the page as a JSON script
    // tag (#dyncol-i18n). Each key maps to a Polish/English string the
    // view resolved through Django's catalog. Falls back to the literal
    // English string when the tag is missing or a key is undefined — so
    // the picker still works if a custom template forgets to embed the
    // dict.
    var I18N = {};
    (function loadI18n() {
        var el = document.getElementById("dyncol-i18n");
        if (!el) return;
        try {
            var parsed = JSON.parse(el.textContent);
            if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
                I18N = parsed;
            }
        } catch (e) {
            // Leave I18N as the empty default; fall back to literals.
        }
    })();

    function tr(key, fallback) {
        if (I18N && Object.prototype.hasOwnProperty.call(I18N, key)) {
            return I18N[key];
        }
        return fallback;
    }

    function updateStatus(scope, hasPersonal) {
        var status = document.getElementById("dyncol-status");
        if (!status) return;
        var msg;
        if (scope === "global") {
            msg = tr(
                "editing_global",
                "Editing the global defaults. Every user without a personal layout will see these columns.",
            );
        } else if (hasPersonal) {
            msg = tr(
                "personal_active",
                "★ You are viewing your personal layout. Saves apply only to your account.",
            );
        } else {
            msg = tr(
                "global_defaults_status",
                "You are viewing the global defaults. Saving will create a personal layout for your account.",
            );
        }
        status.textContent = msg;
    }

    function updateResetButton(scope, hasPersonal) {
        var btn = document.getElementById("dyncol-reset");
        if (!btn) return;
        if (scope === "personal") {
            btn.hidden = !hasPersonal;
            btn.textContent = tr("discard_personal", "Discard personal layout");
        } else {
            btn.hidden = false;
            btn.textContent = tr(
                "reset_global",
                "Reset global defaults from code",
            );
        }
    }

    ready(function () {
        var button = document.getElementById("dyncol-button");
        var modal = document.getElementById("dyncol-modal");
        if (!button || !modal) return;
        activeModal = modal;

        var list = modal.querySelector(".dyncol-list");
        var emptyEl = document.getElementById("dyncol-empty");
        list.dataset.emptyLabel = emptyEl ? emptyEl.textContent : "";

        var data = {
            personal: readPayload("dyncol-personal-data"),
            global: readPayload("dyncol-global-data"),
        };
        var hasPersonal = button.dataset.hasPersonal === "1";

        function render(scope) {
            renderList(list, data[scope] || []);
            updateStatus(scope, hasPersonal);
            updateResetButton(scope, hasPersonal);
        }

        render("personal");

        button.addEventListener("click", function (event) {
            event.preventDefault();
            openModal(modal);
        });

        modal.querySelectorAll("[data-dyncol-close]").forEach(function (el) {
            el.addEventListener("click", function (event) {
                event.preventDefault();
                closeModal(modal);
            });
        });

        modal.querySelectorAll("input[name='dyncol-scope']").forEach(
            function (radio) {
                radio.addEventListener("change", function () {
                    render(radio.value);
                });
            },
        );

        var saveBtn = document.getElementById("dyncol-save");
        if (saveBtn) {
            saveBtn.addEventListener("click", function () {
                var scope = currentScope(modal);
                var payload = {
                    scope: scope,
                    columns: collectPayload(list),
                };
                saveBtn.disabled = true;
                postJson(button.dataset.saveUrl, payload)
                    .then(function (response) {
                        if (response.ok) {
                            window.location.reload();
                        } else {
                            saveBtn.disabled = false;
                            response.text().then(function (body) {
                                window.alert(
                                    tr("save_failed", "Failed to save columns: ") + body,
                                );
                            });
                        }
                    })
                    .catch(function (err) {
                        saveBtn.disabled = false;
                        window.alert(
                            tr("save_failed", "Failed to save columns: ") + err,
                        );
                    });
            });
        }

        var resetBtn = document.getElementById("dyncol-reset");
        if (resetBtn) {
            resetBtn.addEventListener("click", function () {
                var scope = currentScope(modal);
                var msg =
                    scope === "global"
                        ? tr(
                              "confirm_reset_global",
                              "Reset the GLOBAL defaults? They will be re-derived from code on the next changelist load.",
                          )
                        : tr(
                              "confirm_discard_personal",
                              "Discard your personal column layout and use the defaults?",
                          );
                if (!window.confirm(msg)) return;
                resetBtn.disabled = true;
                postJson(button.dataset.resetUrl, { scope: scope }).then(
                    function (response) {
                        if (response.ok) {
                            window.location.reload();
                        } else {
                            resetBtn.disabled = false;
                            window.alert(tr("reset_failed", "Failed to reset."));
                        }
                    },
                );
            });
        }
    });
})();
