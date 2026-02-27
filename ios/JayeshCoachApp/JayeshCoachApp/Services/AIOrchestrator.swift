import Foundation

struct CoachRequest: Encodable {
    let context: String
    let goal: String
    let track: CoachingTrack
}

struct CoachResponse: Decodable {
    let message: String
    let suggestedActions: [String]
}

enum AIOrchestratorError: Error {
    case invalidResponse
}

final class AIOrchestrator {
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func coach(request: CoachRequest, endpoint: String, token: String) async throws -> CoachResponse {
        guard let baseURL = URL(string: endpoint) else {
            throw AIOrchestratorError.invalidResponse
        }
        var urlRequest = URLRequest(url: baseURL.appendingPathComponent("coach/respond"))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if !token.isEmpty {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        urlRequest.httpBody = try JSONEncoder().encode(request)

        let (data, response) = try await session.data(for: urlRequest)
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw AIOrchestratorError.invalidResponse
        }
        return try JSONDecoder().decode(CoachResponse.self, from: data)
    }
}
