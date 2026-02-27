import Foundation

struct RemoteCoachTurnResponse: Decodable {
    let message: String
    let suggestedActions: [String]
    let conversationID: Int

    private enum CodingKeys: String, CodingKey {
        case message
        case suggestedActions = "suggested_actions"
        case conversationID = "conversation_id"
    }
}

struct ResearchBriefItem: Decodable, Identifiable {
    let id: String
    let title: String
    let publishedDate: String
    let category: String
    let takeaway: String
    let application: String
    let sourceURL: String

    private enum CodingKeys: String, CodingKey {
        case id
        case title
        case publishedDate = "published_date"
        case category
        case takeaway
        case application
        case sourceURL = "source_url"
    }
}

final class CoachConversationClient {
    private let session: URLSession
    private let keychain: KeychainStore
    private let serviceName = "JayeshCoach"

    private var endpoint: String {
        UserDefaults.standard.string(forKey: "coach_backend_endpoint") ?? ""
    }

    private var apiKey: String {
        keychain.load(service: serviceName, account: "backend_api_key") ?? ""
    }

    init(session: URLSession = .shared, keychain: KeychainStore) {
        self.session = session
        self.keychain = keychain
    }

    func loadConfig() -> (endpoint: String, apiKey: String) {
        (endpoint, apiKey)
    }

    func saveConfig(endpoint: String, apiKey: String) {
        UserDefaults.standard.set(endpoint, forKey: "coach_backend_endpoint")
        keychain.save(value: apiKey, service: serviceName, account: "backend_api_key")
    }

    func sendMessage(
        userID: String,
        sessionID: String,
        message: String,
        context: String,
        intent: CoachIntent
    ) async throws -> RemoteCoachTurnResponse {
        guard let baseURL = URL(string: endpoint), !apiKey.isEmpty else {
            throw URLError(.userAuthenticationRequired)
        }

        var request = URLRequest(url: baseURL.appendingPathComponent("coach/conversations/message"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")

        let body: [String: Any] = [
            "user_id": userID,
            "session_id": sessionID,
            "message": message,
            "context": context,
            "goal": "Give practical coaching actions grounded in long-term goals.",
            "track": intent.rawValue
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(RemoteCoachTurnResponse.self, from: data)
    }

    func fetchResearchBrief(limit: Int = 5) async throws -> [ResearchBriefItem] {
        guard let baseURL = URL(string: endpoint), !apiKey.isEmpty else {
            throw URLError(.userAuthenticationRequired)
        }
        var components = URLComponents(url: baseURL.appendingPathComponent("coach/intelligence/brief"), resolvingAgainstBaseURL: false)
        components?.queryItems = [URLQueryItem(name: "limit", value: String(limit))]
        guard let url = components?.url else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode([ResearchBriefItem].self, from: data)
    }
}
