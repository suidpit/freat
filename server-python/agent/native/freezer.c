#include "glib.h"
#include <string.h>

#define MAX_FREEZE_ENTRIES 64
#define MODE_FREEZE 0
#define MODE_SCALE  1

#define U8     0
#define U16    1
#define U32    2
#define U64    3
#define FLOAT  4
#define DOUBLE 5

typedef struct {
    uintptr_t address;
    guint8 value[8]; // freeze value or scale factor
    guint8 last_written[8]; // last written value to prevent no-stop multiplications when scaling
    guint32 size;
    guint32 mode;
    guint32 data_type;
    guint32 _pad;
} FreezeEntry;

/* The state must be allocated externally via Memory.alloc()
   and passed in through the CModule symbols argument.
   CModules global variables are read-only. */
extern FreezeEntry entries[MAX_FREEZE_ENTRIES];
extern gint entry_count;
extern volatile gint running;
extern GThread *freeze_thread;
extern GMutex freeze_mutex;

#define DEFINE_SCALE_HELPER(fn_name, type) \
    static void fn_name(FreezeEntry *e) { \
        void *addr = (void *)e->address; \
        type cur = *(type *)addr; \
        type last = *(type *)e->last_written; \
        if (cur == last) return; \
        type scale = *(type *)e->value; \
        type result = cur * scale; \
        *(type *)addr = result; \
        *(type *)e->last_written = result; \
    }

DEFINE_SCALE_HELPER(scale_i8,  gint8)
DEFINE_SCALE_HELPER(scale_i16, gint16)
DEFINE_SCALE_HELPER(scale_i32, gint32)
DEFINE_SCALE_HELPER(scale_i64, gint64)
DEFINE_SCALE_HELPER(scale_f32, gfloat)
DEFINE_SCALE_HELPER(scale_f64, gdouble)

static void scale_entry(FreezeEntry *e) {
    switch (e->data_type) {
    case U8:     scale_i8(e);  break;
    case U16:    scale_i16(e); break;
    case U32:    scale_i32(e); break;
    case U64:    scale_i64(e); break;
    case FLOAT:  scale_f32(e); break;
    case DOUBLE: scale_f64(e); break;
    }
}

static gpointer freeze_loop(gpointer data) {
    (void)data;
    while (running) {
        g_mutex_lock(&freeze_mutex);
        gint count = entry_count;
        for (gint i = 0; i < count; i++) {
            switch (entries[i].mode) {
            case MODE_FREEZE:
                memcpy((void *)entries[i].address, entries[i].value, entries[i].size);
                break;
            case MODE_SCALE:
                scale_entry(&entries[i]);
                break;
            }
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

void freeze_add(uintptr_t address, const void *value_ptr, guint32 size,
                guint32 mode, guint32 data_type) {
    if (size > 8)
        return;

    g_mutex_lock(&freeze_mutex);

    // Update existing entry if address matches
    for (gint i = 0; i < entry_count; i++) {
        if (entries[i].address == address) {
            memcpy(entries[i].value, value_ptr, size);
            entries[i].size = size;
            entries[i].mode = mode;
            entries[i].data_type = data_type;
            memset(entries[i].last_written, 0, 8);
            g_mutex_unlock(&freeze_mutex);
            return;
        }
    }

    // Add new entry
    if (entry_count < MAX_FREEZE_ENTRIES) {
        entries[entry_count].address = address;
        memcpy(entries[entry_count].value, value_ptr, size);
        entries[entry_count].size = size;
        entries[entry_count].mode = mode;
        entries[entry_count].data_type = data_type;
        memset(entries[entry_count].last_written, 0, 8);
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
