#include "glib.h"
#include <string.h>

#define MAX_FREEZE_ENTRIES 64

typedef struct {
    uintptr_t address;
    guint8 value[8];
    guint32 size;
} FreezeEntry;

/* The state must be allocated externally via Memory.alloc()
   and passed in through the CModule symbols argument.
   CModules global variables are read-only. */
extern FreezeEntry entries[MAX_FREEZE_ENTRIES];
extern gint entry_count;
extern volatile gint running;
extern GThread *freeze_thread;
extern GMutex freeze_mutex;
static gpointer freeze_loop(gpointer data) {
    (void)data;
    while (running) {
        g_mutex_lock(&freeze_mutex);
        gint count = entry_count;
        for (gint i = 0; i < count; i++) {
            memcpy((void *)entries[i].address, entries[i].value, entries[i].size);
        }
        g_mutex_unlock(&freeze_mutex);
        g_usleep(100);
    }
    return NULL;
}

void freeze_start(void) {
    if (running)
        return;
    g_mutex_init(&freeze_mutex);
    running = 1;
    freeze_thread = g_thread_new("freat-freezer", freeze_loop, NULL);
}

void freeze_stop(void) {
    if (!running)
        return;
    running = 0;
    if (freeze_thread != NULL) {
        g_thread_join(freeze_thread);
        freeze_thread = NULL;
    }
    g_mutex_clear(&freeze_mutex);
}

void freeze_add(uintptr_t address, const void *value_ptr, guint32 size) {
    if (size > 8)
        return;

    g_mutex_lock(&freeze_mutex);

    // Update existing entry if address matches
    for (gint i = 0; i < entry_count; i++) {
        if (entries[i].address == address) {
            memcpy(entries[i].value, value_ptr, size);
            entries[i].size = size;
            g_mutex_unlock(&freeze_mutex);
            return;
        }
    }

    // Add new entry
    if (entry_count < MAX_FREEZE_ENTRIES) {
        entries[entry_count].address = address;
        memcpy(entries[entry_count].value, value_ptr, size);
        entries[entry_count].size = size;
        entry_count++;
    }

    g_mutex_unlock(&freeze_mutex);
}

void freeze_remove(uintptr_t address) {
    g_mutex_lock(&freeze_mutex);
    for (gint i = 0; i < entry_count; i++) {
        if (entries[i].address == address) {
            // Move last entry into this slot
            if (i < entry_count - 1) {
                entries[i] = entries[entry_count - 1];
            }
            entry_count--;
            g_mutex_unlock(&freeze_mutex);
            return;
        }
    }
    g_mutex_unlock(&freeze_mutex);
}

void freeze_clear(void) {
    g_mutex_lock(&freeze_mutex);
    entry_count = 0;
    g_mutex_unlock(&freeze_mutex);
}
