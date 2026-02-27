import SwiftUI

extension Color {
    static let brandPrimary = Color(red: 0.10, green: 0.24, blue: 0.20)
    static let brandAccent = Color(red: 0.86, green: 0.52, blue: 0.21)
    static let brandSoft = Color(red: 0.95, green: 0.93, blue: 0.88)
    static let brandInk = Color(red: 0.12, green: 0.14, blue: 0.16)
    static let brandMoss = Color(red: 0.30, green: 0.50, blue: 0.42)
    static let brandCard = Color(red: 0.99, green: 0.98, blue: 0.95)
}

extension Font {
    static let coachDisplay = Font.system(size: 31, weight: .black, design: .rounded)
    static let coachTitle = Font.system(size: 20, weight: .bold, design: .rounded)
    static let coachHeadline = Font.system(size: 17, weight: .semibold, design: .rounded)
    static let coachBody = Font.system(size: 15, weight: .regular, design: .serif)
    static let coachCaption = Font.system(size: 12, weight: .medium, design: .rounded)
}

struct CoachBackdrop: View {
    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color.brandSoft,
                    Color(red: 0.92, green: 0.90, blue: 0.84)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            Circle()
                .fill(Color.brandAccent.opacity(0.12))
                .frame(width: 260, height: 260)
                .offset(x: 130, y: -290)
                .blur(radius: 10)

            Circle()
                .fill(Color.brandMoss.opacity(0.17))
                .frame(width: 240, height: 240)
                .offset(x: -150, y: 360)
                .blur(radius: 12)
        }
    }
}

struct CoachStatChip: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.coachCaption)
                .foregroundStyle(Color.white.opacity(0.75))
            Text(value)
                .font(.coachHeadline)
                .foregroundStyle(.white)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(Color.white.opacity(0.14))
        )
    }
}

struct CoachPrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.coachHeadline)
            .foregroundStyle(.white)
            .padding(.horizontal, 15)
            .padding(.vertical, 10)
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [Color.brandPrimary, Color.brandMoss],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
            )
            .scaleEffect(configuration.isPressed ? 0.985 : 1.0)
            .opacity(configuration.isPressed ? 0.92 : 1.0)
    }
}

struct CoachSecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.coachHeadline)
            .foregroundStyle(Color.brandPrimary)
            .padding(.horizontal, 14)
            .padding(.vertical, 9)
            .background(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(Color.white.opacity(0.82))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(Color.brandPrimary.opacity(0.18), lineWidth: 1)
            )
            .scaleEffect(configuration.isPressed ? 0.985 : 1.0)
            .opacity(configuration.isPressed ? 0.92 : 1.0)
    }
}

extension View {
    func coachCardSurface() -> some View {
        background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(Color.brandCard.opacity(0.94))
                .overlay(
                    RoundedRectangle(cornerRadius: 20, style: .continuous)
                        .stroke(Color.white.opacity(0.8), lineWidth: 1)
                )
                .shadow(color: Color.black.opacity(0.06), radius: 14, x: 0, y: 8)
        )
    }
}

struct CoachCard<Content: View>: View {
    let title: String
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.coachTitle)
                .foregroundStyle(Color.brandPrimary)
            content
                .font(.coachBody)
                .foregroundStyle(Color.brandInk)
        }
        .padding(16)
        .coachCardSurface()
    }
}
