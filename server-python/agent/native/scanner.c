#include "glib.h"
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

extern void onMessage(const gchar *message);
static void log(const gchar * format, ...);

typedef enum {
  EXACT,
  LESS_THAN,
  GREATER_THAN,
} ScanType;

typedef enum {
    U8,
    U16,
    U32,
    U64,
    FLOAT,
    DOUBLE,
} ScanSize;


#define DEFINE_SCAN_HELPER(fn_name, type, alignment) \
static GArray * fn_name( \
    uintptr_t base_addr, \
    gsize region_size, \
    void *value_ptr, \
    ScanType scan_type) { \
        log("(%s) Scanning %s at %p with size %zu", #fn_name, #type, base_addr, region_size); \
        GArray *results_array = g_array_new(FALSE, FALSE, sizeof(uintptr_t)); \
        if (results_array == NULL) { \
            return NULL; \
        } \
        type value_to_scan = *(type *)value_ptr; \
        const guint step = alignment; \
        uintptr_t end_addr = base_addr + region_size; \
        for (uintptr_t p = base_addr; p <= end_addr - step; p += step) { \
            type value_at_addr = *(type *)(p); \
            gboolean match = FALSE; \
            switch (scan_type) { \
                case EXACT: \
                    if (value_at_addr == value_to_scan) { \
                        match = TRUE; \
                    } \
                    break; \
                case LESS_THAN: \
                    if (value_at_addr < value_to_scan) { \
                        match = TRUE; \
                    } \
                    break; \
                case GREATER_THAN: \
                    if (value_at_addr > value_to_scan) { \
                        match = TRUE; \
                    } \
                    break; \
            } \
            if (match) { \
                g_array_append_val(results_array, p); \
            } \
        } \
        return results_array; \
    }

DEFINE_SCAN_HELPER(scan_helper_u8, guint8, 1)
DEFINE_SCAN_HELPER(scan_helper_u16, guint16, 2)
DEFINE_SCAN_HELPER(scan_helper_u32, guint32, 4)
DEFINE_SCAN_HELPER(scan_helper_u64, guint64, 8)
DEFINE_SCAN_HELPER(scan_helper_float, gfloat, 4)
DEFINE_SCAN_HELPER(scan_helper_double, gdouble, 8)

uintptr_t * scan_region(
    uintptr_t base_addr,
    size_t region_size,
    ScanType scan_type,
    ScanSize scan_size,
    void *value_ptr,
    gsize *out_count) {
        GArray *results_array = NULL;
        log("Scanning region at 0x%lx with size %zu bytes, scan type %d, scan size %d", base_addr, region_size, scan_type, scan_size);

        switch (scan_size) {
            case U8:
                results_array = scan_helper_u8(base_addr, region_size, value_ptr, scan_type);
                break;
            case U16:
                results_array = scan_helper_u16(base_addr, region_size, value_ptr, scan_type);
                break;
            case U32:
                results_array = scan_helper_u32(base_addr, region_size, value_ptr, scan_type);
                break;
            case U64:
                results_array = scan_helper_u64(base_addr, region_size, value_ptr, scan_type);
                break;
            case FLOAT:
                results_array = scan_helper_float(base_addr, region_size, value_ptr, scan_type);
                break;
            case DOUBLE:
                results_array = scan_helper_double(base_addr, region_size, value_ptr, scan_type);
                break;
            default:
                *out_count = 0;
                return NULL;
        }
        *out_count = results_array->len;
        // Free the array structure, but return the array data
        return (uintptr_t *)g_array_free(results_array, FALSE);
    }

void free_scan_results(uintptr_t *results_ptr) {
    g_free(results_ptr);
}
