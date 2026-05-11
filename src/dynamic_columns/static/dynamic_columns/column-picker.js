/*
 * django-dynamic-columns — column picker UI.
 *
 * Vanilla JS, no external libraries. Native HTML5 drag-and-drop for
 * desktop. The picker writes to /admin/<app>/<model>/dynamic-columns/save/
 * via JSON POST, then reloads to pick up the new ``list_display``.
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

    function ready(fn) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", fn);
        } else {
            fn();
        }
    }

    function setupDragAndDrop(list) {
        var dragged = null;

        function clearDropTargets() {
            list.querySelectorAll(".dyncol-drop-target").forEach(function (el) {
                el.classList.remove("dyncol-drop-target");
            });
        }

        list.querySelectorAll(".dyncol-item").forEach(function (item) {
            item.addEventListener("dragstart", function (event) {
                dragged = item;
                item.classList.add("dyncol-dragging");
                if (event.dataTransfer) {
                    event.dataTransfer.effectAllowed = "move";
                    // Firefox refuses to start a drag without dataTransfer.setData
                    event.dataTransfer.setData("text/plain", item.dataset.colName || "");
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
                if (!dragged || dragged === item) {
                    return;
                }
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
                if (!dragged || dragged === item) {
                    return;
                }
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
                "X-CSRFToken": getCookie("csrftoken") || "",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify(payload || {}),
        });
    }

    function openModal(modal) {
        modal.hidden = false;
        var first = modal.querySelector(".dyncol-item, .dyncol-btn-save");
        if (first) {
            first.focus();
        }
        document.addEventListener("keydown", escapeListener);
    }

    function closeModal(modal) {
        modal.hidden = true;
        document.removeEventListener("keydown", escapeListener);
    }

    var activeModal = null;
    function escapeListener(event) {
        if (event.key === "Escape" && activeModal) {
            closeModal(activeModal);
        }
    }

    ready(function () {
        var button = document.getElementById("dyncol-button");
        var modal = document.getElementById("dyncol-modal");
        if (!button || !modal) {
            return;
        }
        activeModal = modal;

        var list = modal.querySelector(".dyncol-list");
        if (list) {
            setupDragAndDrop(list);
        }

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

        var saveBtn = document.getElementById("dyncol-save");
        if (saveBtn) {
            saveBtn.addEventListener("click", function () {
                var payload = { columns: collectPayload(list) };
                saveBtn.disabled = true;
                postJson(button.dataset.saveUrl, payload).then(function (response) {
                    if (response.ok) {
                        window.location.reload();
                    } else {
                        saveBtn.disabled = false;
                        response.text().then(function (body) {
                            window.alert("Failed to save columns: " + body);
                        });
                    }
                }).catch(function (err) {
                    saveBtn.disabled = false;
                    window.alert("Failed to save columns: " + err);
                });
            });
        }

        var resetBtn = document.getElementById("dyncol-reset");
        if (resetBtn) {
            resetBtn.addEventListener("click", function () {
                if (!window.confirm("Discard your personal column layout and use the defaults?")) {
                    return;
                }
                resetBtn.disabled = true;
                postJson(button.dataset.resetUrl, {}).then(function (response) {
                    if (response.ok) {
                        window.location.reload();
                    } else {
                        resetBtn.disabled = false;
                        window.alert("Failed to reset.");
                    }
                });
            });
        }
    });
})();
