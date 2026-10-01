pragma Singleton
import QtQuick 2.15

QtObject {
    readonly property color background: "#0A0E1A"
    readonly property color surface: "#111827"
    readonly property color surfaceElevated: "#1E293B"
    readonly property color card: "#161F30"
    readonly property color border: "#26334D"

    readonly property color primary: "#6366F1"
    readonly property color primaryLight: "#818CF8"
    readonly property color primaryHover: "#4F46E5"
    readonly property color secondary: "#8B5CF6"

    readonly property color success: "#10B981"
    readonly property color warning: "#F59E0B"
    readonly property color error: "#EF4444"

    readonly property color textPrimary: "#F8FAFC"
    readonly property color textSecondary: "#94A3B8"
    readonly property color textMuted: "#64748B"

    readonly property int radiusSm: 8
    readonly property int radiusMd: 12
    readonly property int radiusLg: 16
    readonly property int radiusXl: 20
}
