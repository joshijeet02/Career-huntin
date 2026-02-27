import Foundation

final class LocalStore {
    private let fm = FileManager.default

    private func url(for file: String) -> URL {
        let base = fm.urls(for: .documentDirectory, in: .userDomainMask).first ?? URL(fileURLWithPath: NSTemporaryDirectory())
        return base.appendingPathComponent(file)
    }

    func save<T: Encodable>(_ value: T, to file: String) {
        do {
            let data = try JSONEncoder.pretty.encode(value)
            try data.write(to: url(for: file), options: [.atomic])
        } catch {
            print("save failed: \(error)")
        }
    }

    func load<T: Decodable>(_ type: T.Type, from file: String) -> T? {
        do {
            let data = try Data(contentsOf: url(for: file))
            return try JSONDecoder.standard.decode(type, from: data)
        } catch {
            return nil
        }
    }
}

private extension JSONEncoder {
    static var pretty: JSONEncoder {
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted, .sortedKeys]
        enc.dateEncodingStrategy = .iso8601
        return enc
    }
}

private extension JSONDecoder {
    static var standard: JSONDecoder {
        let dec = JSONDecoder()
        dec.dateDecodingStrategy = .iso8601
        return dec
    }
}
