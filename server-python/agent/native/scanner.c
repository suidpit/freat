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
  INCREASED,
  DECREASED,
  UNKNOWN,
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
    ScanType scan_type, \
    GArray *out_values) { \
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
                case UNKNOWN: \
                    match = TRUE; \
                    break; \
                default: \
                    break; \
            } \
            if (match) { \
                g_array_append_val(results_array, p); \
                g_array_append_val(out_values, value_at_addr); \
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

static gsize scan_size_bytes(ScanSize scan_size) {
    switch (scan_size) {
        case U8:     return sizeof(guint8);
        case U16:    return sizeof(guint16);
        case U32:    return sizeof(guint32);
        case U64:    return sizeof(guint64);
        case FLOAT:  return sizeof(gfloat);
        case DOUBLE: return sizeof(gdouble);
        default:     return 0;
    }
}

uintptr_t * scan_region(
    uintptr_t base_addr,
    size_t region_size,
    ScanType scan_type,
    ScanSize scan_size,
    void *value_ptr,
    gsize *out_count,
    void **out_values_ptr) {
        gsize elem_size = scan_size_bytes(scan_size);
        if (elem_size == 0) {
            *out_count = 0;
            *out_values_ptr = NULL;
            return NULL;
        }
        GArray *values_array = g_array_new(FALSE, FALSE, elem_size);
        GArray *results_array = NULL;
        switch (scan_size) {
            case U8:
                results_array = scan_helper_u8(base_addr, region_size, value_ptr, scan_type, values_array);
                break;
            case U16:
                results_array = scan_helper_u16(base_addr, region_size, value_ptr, scan_type, values_array);
                break;
            case U32:
                results_array = scan_helper_u32(base_addr, region_size, value_ptr, scan_type, values_array);
                break;
            case U64:
                results_array = scan_helper_u64(base_addr, region_size, value_ptr, scan_type, values_array);
                break;
            case FLOAT:
                results_array = scan_helper_float(base_addr, region_size, value_ptr, scan_type, values_array);
                break;
            case DOUBLE:
                results_array = scan_helper_double(base_addr, region_size, value_ptr, scan_type, values_array);
                break;
            default:
                *out_count = 0;
                *out_values_ptr = NULL;
                g_array_free(values_array, TRUE);
                return NULL;
        }
        *out_count = results_array->len;
        *out_values_ptr = g_array_free(values_array, FALSE);
        return (uintptr_t *)g_array_free(results_array, FALSE);
    }

#define DEFINE_FILTER_HELPER(fn_name, type) \
static GArray * fn_name( \
    uintptr_t * prev_results, \
    gsize prev_count, \
    void *value_ptr, \
    void *prev_values, \
    ScanType scan_type, \
    GArray *out_values) { \
        log("(%s) Filtering %s at %p (#%zu elements)", #fn_name, #type, prev_results, prev_count); \
        GArray *new_results = g_array_new(FALSE, FALSE, sizeof(uintptr_t)); \
        if (new_results == NULL) { \
            return NULL; \
        } \
        type value_to_scan = *(type *)value_ptr; \
        type *prev_vals = (type *)prev_values; \
        for (guint i = 0; i < prev_count; i++) { \
            uintptr_t p = prev_results[i]; \
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
                case INCREASED: \
                    if (value_at_addr > prev_vals[i]) { \
                        match = TRUE; \
                    } \
                    break; \
                case DECREASED: \
                    if (value_at_addr < prev_vals[i]) { \
                        match = TRUE; \
                    } \
                    break; \
            } \
            if (match) { \
                g_array_append_val(new_results, p); \
                g_array_append_val(out_values, value_at_addr); \
            } \
        } \
        return new_results; \
    }

DEFINE_FILTER_HELPER(filter_helper_u8, guint8)
DEFINE_FILTER_HELPER(filter_helper_u16, guint16)
DEFINE_FILTER_HELPER(filter_helper_u32, guint32)
DEFINE_FILTER_HELPER(filter_helper_u64, guint64)
DEFINE_FILTER_HELPER(filter_helper_float, gfloat)
DEFINE_FILTER_HELPER(filter_helper_double, gdouble)

uintptr_t * filter_scans(
    uintptr_t * prev_results,
    gsize prev_count,
    ScanType scan_type,
    ScanSize scan_size,
    void * value_ptr,
    void * prev_values,
    uintptr_t * out_count,
    void ** out_values_ptr
) {
    gsize elem_size = scan_size_bytes(scan_size);
    GArray *values_array = g_array_new(FALSE, FALSE, elem_size);
    GArray *new_results = NULL;
    switch (scan_size) {
        case U8:
            new_results = filter_helper_u8(prev_results, prev_count, value_ptr, prev_values, scan_type, values_array);
            break;
        case U16:
            new_results = filter_helper_u16(prev_results, prev_count, value_ptr, prev_values, scan_type, values_array);
            break;
        case U32:
            new_results = filter_helper_u32(prev_results, prev_count, value_ptr, prev_values, scan_type, values_array);
            break;
        case U64:
            new_results = filter_helper_u64(prev_results, prev_count, value_ptr, prev_values, scan_type, values_array);
            break;
        case FLOAT:
            new_results = filter_helper_float(prev_results, prev_count, value_ptr, prev_values, scan_type, values_array);
            break;
        case DOUBLE:
            new_results = filter_helper_double(prev_results, prev_count, value_ptr, prev_values, scan_type, values_array);
            break;
    }

    *out_count = new_results->len;
    *out_values_ptr = g_array_free(values_array, FALSE);
    return (uintptr_t *)g_array_free(new_results, FALSE);
}

gboolean find_address_in_results(uintptr_t * results, gsize count, uintptr_t addr) {
    for (gsize i = 0; i < count; i++) {
        if (results[i] == addr) {
            return TRUE;
        }
    }
    return FALSE;
}

void free_results(uintptr_t *results_ptr) {
    g_free(results_ptr);
}

static void log(const gchar *format, ...) {
    gchar *message;
    va_list args;
    va_start(args, format);
    message = g_strdup_vprintf(format, args);
    va_end(args);
    onMessage(message);
    g_free(message);
}
