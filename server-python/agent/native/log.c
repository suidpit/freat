static void log(const gchar *format, ...) {
    gchar *message;
    va_list args;
    va_start(args, format);
    message = g_strdup_vprintf(format, args);
    va_end(args);
    onMessage(message);
    g_free(message);
}
