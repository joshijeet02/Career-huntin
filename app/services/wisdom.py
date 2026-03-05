"""
Spiritual Intelligence service.

Provides three capabilities:
  1. seed_wisdom_corpus(db)          — populate the DB with curated teachings on first run
  2. get_contextual_wisdom(uid, db)  — pick the most relevant teaching for a user's current state
  3. ask_masters(question, uid, db)  — synthesize wisdom from the corpus via AI, with citations

Corpus: 22 traditions, ~110 entries, 2,500 years of human wisdom.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
from datetime import date, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import DailyCheckIn, SpiritualWisdom, UserProfile

# ── Curated corpus ────────────────────────────────────────────────────────────
# Each entry: (master, tradition, era, quote, source, themes, reflection, is_scripture)
# Themes: leadership | ego | discipline | service | equanimity | suffering |
#         purpose | truth | relationships | courage | impermanence | work |
#         mind | consciousness | love | surrender | wisdom | adversity |
#         self-knowledge | gratitude

CORPUS: list[dict] = [
    # ── Bhagavad Gita ─────────────────────────────────────────────────────────
    {
        "master": "Bhagavad Gita",
        "tradition": "Hindu",
        "era": "~500 BCE",
        "quote": "You have a right to perform your prescribed duties, but you are not entitled to the fruits of your actions. Never consider yourself the cause of results, and never be attached to not doing your duty.",
        "source": "Bhagavad Gita 2.47",
        "themes": ["work", "discipline", "ego", "leadership"],
        "reflection": "The foundation of karma yoga — act fully, cling to nothing.",
        "is_scripture": True,
    },
    {
        "master": "Bhagavad Gita",
        "tradition": "Hindu",
        "era": "~500 BCE",
        "quote": "The mind is restless and difficult to restrain, but it is subdued by practice and detachment.",
        "source": "Bhagavad Gita 6.35",
        "themes": ["mind", "discipline", "equanimity", "self-knowledge"],
        "reflection": "Mastery of mind is a lifelong practice — not a destination.",
        "is_scripture": True,
    },
    {
        "master": "Bhagavad Gita",
        "tradition": "Hindu",
        "era": "~500 BCE",
        "quote": "The soul is never born nor dies at any time. It is unborn, eternal, ever-existing, and primeval. It is not slain when the body is slain.",
        "source": "Bhagavad Gita 2.20",
        "themes": ["impermanence", "consciousness", "purpose", "suffering"],
        "reflection": "Fear of loss dissolves when we see what is truly permanent.",
        "is_scripture": True,
    },
    {
        "master": "Bhagavad Gita",
        "tradition": "Hindu",
        "era": "~500 BCE",
        "quote": "Reshape yourself through the power of your will; never let yourself be degraded by self-will. The mind is both the friend and the enemy of the self.",
        "source": "Bhagavad Gita 6.5",
        "themes": ["self-knowledge", "discipline", "mind", "leadership"],
        "reflection": "You are both the problem and the solution — the question is which will you choose.",
        "is_scripture": True,
    },
    {
        "master": "Bhagavad Gita",
        "tradition": "Hindu",
        "era": "~500 BCE",
        "quote": "When a man has let go of all desires that arise in the mind, and rests content within himself alone, then he is called a man of steady wisdom.",
        "source": "Bhagavad Gita 2.55",
        "themes": ["equanimity", "ego", "wisdom", "surrender"],
        "reflection": "Contentment is not passivity — it is freedom from compulsive wanting.",
        "is_scripture": True,
    },
    {
        "master": "Bhagavad Gita",
        "tradition": "Hindu",
        "era": "~500 BCE",
        "quote": "Whatever happened, happened for good. Whatever is happening, is happening for good. Whatever will happen, will also happen for good.",
        "source": "Bhagavad Gita — Krishna's teaching",
        "themes": ["surrender", "equanimity", "adversity", "gratitude"],
        "reflection": "Radical trust in the unfolding — not passive acceptance but active faith.",
        "is_scripture": True,
    },
    {
        "master": "Bhagavad Gita",
        "tradition": "Hindu",
        "era": "~500 BCE",
        "quote": "Set thy heart upon thy work, but never on its reward. Work not for a reward; but never cease to do thy work.",
        "source": "Bhagavad Gita 2.47 (Mascaro translation)",
        "themes": ["work", "discipline", "ego", "service"],
        "reflection": "The master craftsman cares only for the quality of the work itself.",
        "is_scripture": True,
    },
    # ── Bible ─────────────────────────────────────────────────────────────────
    {
        "master": "Bible",
        "tradition": "Christian",
        "era": "1st century",
        "quote": "Be still, and know that I am God.",
        "source": "Psalms 46:10",
        "themes": ["surrender", "equanimity", "mind", "consciousness"],
        "reflection": "The deepest wisdom is sometimes accessed in stillness, not in action.",
        "is_scripture": True,
    },
    {
        "master": "Bible",
        "tradition": "Christian",
        "era": "1st century",
        "quote": "For God has not given us a spirit of fear, but of power and of love and of a sound mind.",
        "source": "2 Timothy 1:7",
        "themes": ["courage", "leadership", "mind", "adversity"],
        "reflection": "Fear is not your nature — strength is.",
        "is_scripture": True,
    },
    {
        "master": "Bible",
        "tradition": "Christian",
        "era": "1st century",
        "quote": "Do not be anxious about tomorrow, for tomorrow will be anxious for itself. Let the day's own trouble be sufficient for the day.",
        "source": "Matthew 6:34",
        "themes": ["equanimity", "mind", "adversity", "impermanence"],
        "reflection": "Present-moment focus — the antidote to the tyranny of anticipation.",
        "is_scripture": True,
    },
    {
        "master": "Bible",
        "tradition": "Christian",
        "era": "~10th century BCE",
        "quote": "A gentle answer turns away wrath, but a harsh word stirs up anger.",
        "source": "Proverbs 15:1",
        "themes": ["relationships", "leadership", "truth", "love"],
        "reflection": "Tone is strategy. The leader who speaks softly often wins what the loud one loses.",
        "is_scripture": True,
    },
    {
        "master": "Bible",
        "tradition": "Christian",
        "era": "~10th century BCE",
        "quote": "He who walks with wise men becomes wise, but the companion of fools will suffer harm.",
        "source": "Proverbs 13:20",
        "themes": ["wisdom", "relationships", "leadership", "discipline"],
        "reflection": "Your five closest relationships determine the ceiling of your growth.",
        "is_scripture": True,
    },
    {
        "master": "Bible",
        "tradition": "Christian",
        "era": "1st century",
        "quote": "Whatever you do, work heartily, as for the Lord and not for men.",
        "source": "Colossians 3:23",
        "themes": ["work", "service", "discipline", "purpose"],
        "reflection": "Excellence becomes natural when you work for something larger than approval.",
        "is_scripture": True,
    },
    {
        "master": "Bible",
        "tradition": "Christian",
        "era": "1st century",
        "quote": "Commit your work to the Lord, and your plans will be established.",
        "source": "Proverbs 16:3",
        "themes": ["work", "surrender", "purpose", "leadership"],
        "reflection": "Surrender of outcome does not mean surrender of effort.",
        "is_scripture": True,
    },
    # ── Quran ─────────────────────────────────────────────────────────────────
    {
        "master": "Quran",
        "tradition": "Islamic",
        "era": "7th century",
        "quote": "Indeed, with hardship comes ease.",
        "source": "Surah Ash-Sharh 94:6",
        "themes": ["adversity", "suffering", "equanimity", "courage"],
        "reflection": "Difficulty and relief are not opposites — they coexist in the same moment.",
        "is_scripture": True,
    },
    {
        "master": "Quran",
        "tradition": "Islamic",
        "era": "7th century",
        "quote": "Allah does not burden a soul beyond that it can bear.",
        "source": "Surah Al-Baqarah 2:286",
        "themes": ["adversity", "suffering", "courage", "surrender"],
        "reflection": "The weight you carry is proof of the strength you possess.",
        "is_scripture": True,
    },
    {
        "master": "Quran",
        "tradition": "Islamic",
        "era": "7th century",
        "quote": "And it may be that you dislike a thing which is good for you, and it may be that you like a thing which is bad for you. Allah knows and you do not know.",
        "source": "Surah Al-Baqarah 2:216",
        "themes": ["surrender", "equanimity", "wisdom", "adversity"],
        "reflection": "What looks like loss from inside the moment often looks like grace from outside it.",
        "is_scripture": True,
    },
    {
        "master": "Quran",
        "tradition": "Islamic",
        "era": "7th century",
        "quote": "Do not lose hope, nor be sad.",
        "source": "Surah Al-Imran 3:139",
        "themes": ["adversity", "courage", "equanimity", "suffering"],
        "reflection": "Despair is a choice. Hope is also a choice.",
        "is_scripture": True,
    },
    {
        "master": "Quran",
        "tradition": "Islamic",
        "era": "7th century",
        "quote": "Speak to people good words.",
        "source": "Surah Al-Baqarah 2:83",
        "themes": ["relationships", "leadership", "love", "service"],
        "reflection": "Speech is the most immediate expression of character.",
        "is_scripture": True,
    },
    # ── Ramayana ──────────────────────────────────────────────────────────────
    {
        "master": "Valmiki Ramayana",
        "tradition": "Hindu",
        "era": "~500 BCE",
        "quote": "Truth is the highest virtue; by truth the world is upheld. Truth is the foundation of all good deeds.",
        "source": "Valmiki Ramayana",
        "themes": ["truth", "leadership", "purpose", "service"],
        "reflection": "In every negotiation, every relationship, truth is the only durable currency.",
        "is_scripture": True,
    },
    {
        "master": "Valmiki Ramayana",
        "tradition": "Hindu",
        "era": "~500 BCE",
        "quote": "The noblest person is one who considers the welfare of others as their own welfare.",
        "source": "Valmiki Ramayana",
        "themes": ["service", "leadership", "love", "purpose"],
        "reflection": "Rama's kingship was defined by what he gave, never by what he held.",
        "is_scripture": True,
    },
    {
        "master": "Valmiki Ramayana",
        "tradition": "Hindu",
        "era": "~500 BCE",
        "quote": "A man's greatness is not in his power, but in the use he makes of that power.",
        "source": "Valmiki Ramayana — Rama's dharma",
        "themes": ["leadership", "service", "ego", "purpose"],
        "reflection": "Authority without restraint is force. Authority with restraint is leadership.",
        "is_scripture": True,
    },
    # ── Swami Vivekananda ──────────────────────────────────────────────────────
    {
        "master": "Swami Vivekananda",
        "tradition": "Vedanta",
        "era": "1863–1902",
        "quote": "Arise, awake, and stop not till the goal is reached.",
        "source": "Katha Upanishad (Vivekananda's rallying call)",
        "themes": ["courage", "discipline", "purpose", "leadership"],
        "reflection": "The only failure is stopping. Everything else is momentum.",
        "is_scripture": False,
    },
    {
        "master": "Swami Vivekananda",
        "tradition": "Vedanta",
        "era": "1863–1902",
        "quote": "The greatest sin is to think yourself weak.",
        "source": "Vivekananda's lectures",
        "themes": ["courage", "self-knowledge", "leadership", "adversity"],
        "reflection": "Self-doubt is not humility. It is a subtle form of self-betrayal.",
        "is_scripture": False,
    },
    {
        "master": "Swami Vivekananda",
        "tradition": "Vedanta",
        "era": "1863–1902",
        "quote": "Take up one idea. Make that one idea your life — think of it, dream of it, live on that idea. Let the brain, muscles, nerves, every part of your body, be full of that idea, and just leave every other idea alone. This is the way to success.",
        "source": "Raja Yoga",
        "themes": ["discipline", "purpose", "leadership", "work"],
        "reflection": "Scattered attention is the enemy of mastery.",
        "is_scripture": False,
    },
    {
        "master": "Swami Vivekananda",
        "tradition": "Vedanta",
        "era": "1863–1902",
        "quote": "We are what our thoughts have made us; so take care about what you think. Words are secondary. Thoughts live; they travel far.",
        "source": "Vivekananda's teachings",
        "themes": ["mind", "self-knowledge", "discipline", "consciousness"],
        "reflection": "Every habitual thought is an investment — in growth or in stagnation.",
        "is_scripture": False,
    },
    {
        "master": "Swami Vivekananda",
        "tradition": "Vedanta",
        "era": "1863–1902",
        "quote": "In a conflict between the heart and the brain, follow your heart.",
        "source": "Vivekananda's letters",
        "themes": ["truth", "courage", "self-knowledge", "leadership"],
        "reflection": "The intellect rationalizes. The heart knows.",
        "is_scripture": False,
    },
    {
        "master": "Swami Vivekananda",
        "tradition": "Vedanta",
        "era": "1863–1902",
        "quote": "All power is within you; you can do anything and everything. Believe in that, do not believe that you are weak.",
        "source": "Vivekananda's speeches",
        "themes": ["courage", "self-knowledge", "adversity", "leadership"],
        "reflection": "The source of strength was never outside you.",
        "is_scripture": False,
    },
    # ── Paramahansa Yogananda ──────────────────────────────────────────────────
    {
        "master": "Paramahansa Yogananda",
        "tradition": "Kriya Yoga",
        "era": "1893–1952",
        "quote": "Change yourself and you have done your part in changing the world.",
        "source": "Yogananda's teachings",
        "themes": ["self-knowledge", "purpose", "leadership", "discipline"],
        "reflection": "The revolution that matters most begins inside.",
        "is_scripture": False,
    },
    {
        "master": "Paramahansa Yogananda",
        "tradition": "Kriya Yoga",
        "era": "1893–1952",
        "quote": "Live quietly in the moment and see the beauty of all before you. The future will take care of itself.",
        "source": "Yogananda's teachings",
        "themes": ["equanimity", "impermanence", "mind", "surrender"],
        "reflection": "Presence is not a technique. It is a way of being.",
        "is_scripture": False,
    },
    {
        "master": "Paramahansa Yogananda",
        "tradition": "Kriya Yoga",
        "era": "1893–1952",
        "quote": "The happiness of one's own heart alone cannot satisfy the soul; one must try to include the happiness of others as necessary to one's own happiness.",
        "source": "Autobiography of a Yogi",
        "themes": ["love", "service", "relationships", "purpose"],
        "reflection": "Generosity is not sacrifice — it is the expansion of the self.",
        "is_scripture": False,
    },
    {
        "master": "Paramahansa Yogananda",
        "tradition": "Kriya Yoga",
        "era": "1893–1952",
        "quote": "Remain calm, serene, always in command of yourself. You will then find out how easy it is to get along.",
        "source": "Yogananda's teachings",
        "themes": ["equanimity", "leadership", "relationships", "discipline"],
        "reflection": "The regulated self is the most powerful self.",
        "is_scripture": False,
    },
    # ── Ramana Maharshi ────────────────────────────────────────────────────────
    {
        "master": "Ramana Maharshi",
        "tradition": "Advaita Vedanta",
        "era": "1879–1950",
        "quote": "The mind which has found that it has no separate reality, that it is consciousness itself, sinks into the Heart.",
        "source": "Talks with Ramana Maharshi",
        "themes": ["consciousness", "self-knowledge", "ego", "truth"],
        "reflection": "The ego dissolves not by fighting it, but by seeing through it.",
        "is_scripture": False,
    },
    {
        "master": "Ramana Maharshi",
        "tradition": "Advaita Vedanta",
        "era": "1879–1950",
        "quote": "Happiness is your nature. It is not wrong to desire it. What is wrong is seeking it outside when it is inside.",
        "source": "Be As You Are — David Godman (compilation)",
        "themes": ["self-knowledge", "purpose", "consciousness", "suffering"],
        "reflection": "The search ends when you realize the searcher is what you were seeking.",
        "is_scripture": False,
    },
    {
        "master": "Ramana Maharshi",
        "tradition": "Advaita Vedanta",
        "era": "1879–1950",
        "quote": "If there is anything besides the Self, let it be. What does it matter to you? Let the world take care of itself. If you give up thinking of it and remain as the Self, that is best.",
        "source": "Talks with Ramana Maharshi",
        "themes": ["ego", "equanimity", "surrender", "consciousness"],
        "reflection": "Not indifference — freedom from the compulsion to control everything.",
        "is_scripture": False,
    },
    {
        "master": "Ramana Maharshi",
        "tradition": "Advaita Vedanta",
        "era": "1879–1950",
        "quote": "The degree of freedom from unwanted thoughts and the degree of concentration on a single thought are the measures to gauge spiritual progress.",
        "source": "Ramana Maharshi's teachings",
        "themes": ["mind", "discipline", "consciousness", "self-knowledge"],
        "reflection": "Mental clarity is the beginning of all real clarity.",
        "is_scripture": False,
    },
    # ── Ramakrishna Paramahamsa ────────────────────────────────────────────────
    {
        "master": "Ramakrishna Paramahamsa",
        "tradition": "Hindu / Universal",
        "era": "1836–1886",
        "quote": "Pray to God as if you were a child. A child does not know the intricacies of life; all he needs is his mother. In the same way, all you need is God.",
        "source": "The Gospel of Sri Ramakrishna",
        "themes": ["surrender", "love", "consciousness", "truth"],
        "reflection": "The ego complicates. The pure heart simplifies.",
        "is_scripture": False,
    },
    {
        "master": "Ramakrishna Paramahamsa",
        "tradition": "Hindu / Universal",
        "era": "1836–1886",
        "quote": "As long as I live, so long do I learn. He is never old who continues to learn.",
        "source": "Sayings of Ramakrishna",
        "themes": ["wisdom", "purpose", "discipline", "self-knowledge"],
        "reflection": "Curiosity is not a personality trait — it is a spiritual practice.",
        "is_scripture": False,
    },
    {
        "master": "Ramakrishna Paramahamsa",
        "tradition": "Hindu / Universal",
        "era": "1836–1886",
        "quote": "It is the nature of the lamp to give light. With the help of that light, someone may read scripture, and someone else may commit a forgery. The lamp is not to blame.",
        "source": "The Gospel of Sri Ramakrishna",
        "themes": ["service", "ego", "truth", "leadership"],
        "reflection": "The leader's job is to give light — not to control how others use it.",
        "is_scripture": False,
    },
    # ── Adi Shankaracharya ─────────────────────────────────────────────────────
    {
        "master": "Adi Shankaracharya",
        "tradition": "Advaita Vedanta",
        "era": "788–820 CE",
        "quote": "Seek the Self. That is the only meaningful inquiry. Everything else is transient play.",
        "source": "Vivekachudamani (Crest Jewel of Discrimination)",
        "themes": ["self-knowledge", "consciousness", "truth", "purpose"],
        "reflection": "Before mastering the world, first understand who is doing the mastering.",
        "is_scripture": False,
    },
    {
        "master": "Adi Shankaracharya",
        "tradition": "Advaita Vedanta",
        "era": "788–820 CE",
        "quote": "Renounce the tendency to see yourself as a doer. The sun illumines the world without effort or intention. Be like the sun.",
        "source": "Vivekachudamani",
        "themes": ["ego", "service", "work", "consciousness"],
        "reflection": "The highest leadership is one that gives without the need for credit.",
        "is_scripture": False,
    },
    {
        "master": "Adi Shankaracharya",
        "tradition": "Advaita Vedanta",
        "era": "788–820 CE",
        "quote": "Worship of God should make you forget who you are, only to find a better version of yourself.",
        "source": "Bhaja Govindam",
        "themes": ["ego", "surrender", "self-knowledge", "consciousness"],
        "reflection": "Every practice that dissolves the ego is spiritual practice.",
        "is_scripture": False,
    },
    # ── Kabir ─────────────────────────────────────────────────────────────────
    {
        "master": "Kabir",
        "tradition": "Bhakti / Sufi",
        "era": "1440–1518",
        "quote": "When I was, God was not. When God is, I am not. You cannot have both — this I have understood.",
        "source": "Kabir's Dohas",
        "themes": ["ego", "consciousness", "truth", "self-knowledge"],
        "reflection": "Ego and truth occupy the same space — only one can fill it.",
        "is_scripture": False,
    },
    {
        "master": "Kabir",
        "tradition": "Bhakti / Sufi",
        "era": "1440–1518",
        "quote": "Do not go to the garden of flowers — in your body is the garden of flowers. Take your seat on the thousand petals of the lotus, and there gaze on the infinite beauty.",
        "source": "Kabir's poems",
        "themes": ["consciousness", "self-knowledge", "truth", "wisdom"],
        "reflection": "The ultimate resource has always been inside.",
        "is_scripture": False,
    },
    {
        "master": "Kabir",
        "tradition": "Bhakti / Sufi",
        "era": "1440–1518",
        "quote": "The river that flows in you also flows in me.",
        "source": "Kabir's poems",
        "themes": ["love", "relationships", "consciousness", "service"],
        "reflection": "Separation is the illusion. Connection is the truth.",
        "is_scripture": False,
    },
    {
        "master": "Kabir",
        "tradition": "Bhakti / Sufi",
        "era": "1440–1518",
        "quote": "Speak only when your words are more beautiful than silence.",
        "source": "Kabir's Dohas",
        "themes": ["relationships", "leadership", "truth", "wisdom"],
        "reflection": "Most of what we say adds noise. Silence is often the most powerful response.",
        "is_scripture": False,
    },
    # ── Mahavira / Jainism ─────────────────────────────────────────────────────
    {
        "master": "Mahavira",
        "tradition": "Jain",
        "era": "599–527 BCE",
        "quote": "Do not injure, abuse, oppress, enslave, insult, torment, torture, or kill any creature or living being.",
        "source": "Acaranga Sutra",
        "themes": ["service", "leadership", "truth", "love"],
        "reflection": "The test of character is what we do with power over those weaker than us.",
        "is_scripture": False,
    },
    {
        "master": "Mahavira",
        "tradition": "Jain",
        "era": "599–527 BCE",
        "quote": "Have no attachment to external things — they are transient. The path of right knowledge, right faith, and right conduct — this is the path of liberation.",
        "source": "Jain teachings attributed to Mahavira",
        "themes": ["impermanence", "discipline", "truth", "purpose"],
        "reflection": "Every attachment is a weight. Every release is a step toward freedom.",
        "is_scripture": False,
    },
    {
        "master": "Mahavira",
        "tradition": "Jain",
        "era": "599–527 BCE",
        "quote": "The soul comes alone and goes alone, no one companies it, and no one becomes its mate.",
        "source": "Uttaradhyayana Sutra",
        "themes": ["self-knowledge", "impermanence", "consciousness", "truth"],
        "reflection": "Knowing this, you will hold relationships with open hands — fully present, never possessive.",
        "is_scripture": False,
    },
    # ── Thiruvalluvar / Tirukkural ──────────────────────────────────────────────
    {
        "master": "Thiruvalluvar",
        "tradition": "Tamil / Universal",
        "era": "~1st–4th century CE",
        "quote": "What is there greater than learning? What is there worse than ignorance? What is it to be kind? To do good to all. What is it to be cruel? To do harm to another.",
        "source": "Tirukkural",
        "themes": ["wisdom", "leadership", "service", "truth"],
        "reflection": "The simplest ethical framework ever written: learn, do good, harm none.",
        "is_scripture": False,
    },
    {
        "master": "Thiruvalluvar",
        "tradition": "Tamil / Universal",
        "era": "~1st–4th century CE",
        "quote": "Even if an action fails, doing it rightly is virtuous. Even if an action succeeds, doing it wrongly is ruinous.",
        "source": "Tirukkural",
        "themes": ["work", "truth", "leadership", "discipline"],
        "reflection": "The quality of the action is the only thing fully within your control.",
        "is_scripture": False,
    },
    {
        "master": "Thiruvalluvar",
        "tradition": "Tamil / Universal",
        "era": "~1st–4th century CE",
        "quote": "A kind word spoken in time is worth more than a gift given too late.",
        "source": "Tirukkural",
        "themes": ["relationships", "leadership", "love", "truth"],
        "reflection": "Timeliness is itself an act of care.",
        "is_scripture": False,
    },
    # ── Gautama Buddha ─────────────────────────────────────────────────────────
    {
        "master": "Gautama Buddha",
        "tradition": "Buddhist",
        "era": "563–483 BCE",
        "quote": "The mind is everything. What you think, you become.",
        "source": "Dhammapada",
        "themes": ["mind", "self-knowledge", "discipline", "consciousness"],
        "reflection": "Before the action, there is the thought. Tend to the source.",
        "is_scripture": False,
    },
    {
        "master": "Gautama Buddha",
        "tradition": "Buddhist",
        "era": "563–483 BCE",
        "quote": "Three things cannot long be hidden: the sun, the moon, and the truth.",
        "source": "Buddhist teaching attributed to the Buddha",
        "themes": ["truth", "leadership", "wisdom", "impermanence"],
        "reflection": "You can manage truth's timeline — you cannot change its destination.",
        "is_scripture": False,
    },
    {
        "master": "Gautama Buddha",
        "tradition": "Buddhist",
        "era": "563–483 BCE",
        "quote": "In the end, only three things matter: how much you loved, how gently you lived, and how gracefully you let go of things not meant for you.",
        "source": "Buddhist teaching",
        "themes": ["love", "impermanence", "equanimity", "surrender"],
        "reflection": "Grasping causes suffering. Letting go causes freedom.",
        "is_scripture": False,
    },
    {
        "master": "Gautama Buddha",
        "tradition": "Buddhist",
        "era": "563–483 BCE",
        "quote": "Do not dwell in the past, do not dream of the future, concentrate the mind on the present moment.",
        "source": "Dhammapada",
        "themes": ["mind", "equanimity", "discipline", "impermanence"],
        "reflection": "The present moment is the only place where work, love, and growth actually happen.",
        "is_scripture": False,
    },
    {
        "master": "Gautama Buddha",
        "tradition": "Buddhist",
        "era": "563–483 BCE",
        "quote": "Better than a thousand hollow words is one word that brings peace.",
        "source": "Dhammapada",
        "themes": ["relationships", "leadership", "truth", "wisdom"],
        "reflection": "Depth over volume — in speech as in life.",
        "is_scripture": False,
    },
    {
        "master": "Gautama Buddha",
        "tradition": "Buddhist",
        "era": "563–483 BCE",
        "quote": "You yourself, as much as anybody in the entire universe, deserve your love and affection.",
        "source": "Buddhist teaching",
        "themes": ["love", "self-knowledge", "suffering", "truth"],
        "reflection": "Self-compassion is not weakness — it is the foundation of genuine compassion for others.",
        "is_scripture": False,
    },
    # ── Rumi ──────────────────────────────────────────────────────────────────
    {
        "master": "Rumi",
        "tradition": "Sufi",
        "era": "1207–1273",
        "quote": "Out beyond ideas of wrongdoing and rightdoing, there is a field. I'll meet you there.",
        "source": "Masnavi",
        "themes": ["truth", "relationships", "love", "ego"],
        "reflection": "The hardest conversations become possible when you abandon the need to be right.",
        "is_scripture": False,
    },
    {
        "master": "Rumi",
        "tradition": "Sufi",
        "era": "1207–1273",
        "quote": "The wound is the place where the Light enters you.",
        "source": "Masnavi",
        "themes": ["adversity", "suffering", "consciousness", "wisdom"],
        "reflection": "Your deepest difficulties are not obstacles to growth — they are the path.",
        "is_scripture": False,
    },
    {
        "master": "Rumi",
        "tradition": "Sufi",
        "era": "1207–1273",
        "quote": "Yesterday I was clever, so I wanted to change the world. Today I am wise, so I am changing myself.",
        "source": "Rumi's poems",
        "themes": ["self-knowledge", "wisdom", "leadership", "ego"],
        "reflection": "The direction of real change always moves inward first.",
        "is_scripture": False,
    },
    {
        "master": "Rumi",
        "tradition": "Sufi",
        "era": "1207–1273",
        "quote": "Silence is the ocean of knowledge, and speech is like the river. The ocean seeks the river, but the river finds its way to the ocean.",
        "source": "Masnavi",
        "themes": ["wisdom", "truth", "consciousness", "mind"],
        "reflection": "The most important things in any conversation are never said.",
        "is_scripture": False,
    },
    {
        "master": "Rumi",
        "tradition": "Sufi",
        "era": "1207–1273",
        "quote": "When you do things from your soul, you feel a river moving in you, a joy.",
        "source": "Rumi's poems",
        "themes": ["purpose", "work", "consciousness", "truth"],
        "reflection": "Alignment between your deepest values and your daily actions creates an unmistakable joy.",
        "is_scripture": False,
    },
    {
        "master": "Rumi",
        "tradition": "Sufi",
        "era": "1207–1273",
        "quote": "Be like a tree and let the dead leaves drop.",
        "source": "Rumi's poems",
        "themes": ["impermanence", "ego", "surrender", "discipline"],
        "reflection": "Releasing what no longer serves you is not loss — it is preparation for new growth.",
        "is_scripture": False,
    },
    {
        "master": "Rumi",
        "tradition": "Sufi",
        "era": "1207–1273",
        "quote": "Your task is not to seek for love, but merely to seek and find all the barriers within yourself that you have built against it.",
        "source": "Masnavi",
        "themes": ["love", "ego", "self-knowledge", "relationships"],
        "reflection": "Love is already present. The work is removing what blocks it.",
        "is_scripture": False,
    },
    # ── Al-Ghazali ────────────────────────────────────────────────────────────
    {
        "master": "Al-Ghazali",
        "tradition": "Sufi / Islamic",
        "era": "1058–1111",
        "quote": "Knowledge without action is vanity, and action without knowledge is insanity.",
        "source": "Ihya Ulum al-Din (Revival of the Religious Sciences)",
        "themes": ["wisdom", "work", "discipline", "leadership"],
        "reflection": "The integration of understanding and doing is the mark of real mastery.",
        "is_scripture": False,
    },
    {
        "master": "Al-Ghazali",
        "tradition": "Sufi / Islamic",
        "era": "1058–1111",
        "quote": "Declare your jihad on thirteen enemies you cannot see — egoism, arrogance, conceit, selfishness, greed, lust, intolerance, anger, lying, cheating, gossiping, and slandering.",
        "source": "Al-Ghazali's teachings",
        "themes": ["ego", "discipline", "self-knowledge", "truth"],
        "reflection": "The battles that shape your character are fought inward, not outward.",
        "is_scripture": False,
    },
    {
        "master": "Al-Ghazali",
        "tradition": "Sufi / Islamic",
        "era": "1058–1111",
        "quote": "Silence is the sleep that nourishes wisdom.",
        "source": "Ihya Ulum al-Din",
        "themes": ["wisdom", "mind", "discipline", "consciousness"],
        "reflection": "Most people are not quiet enough to hear what wisdom is trying to say.",
        "is_scripture": False,
    },
    # ── Hafiz ─────────────────────────────────────────────────────────────────
    {
        "master": "Hafiz",
        "tradition": "Sufi / Persian",
        "era": "1325–1390",
        "quote": "Even after all this time, the sun never says to the earth, 'You owe me.' Look what happens with a love like that — it lights the whole sky.",
        "source": "The Gift (Ladinsky translation)",
        "themes": ["love", "service", "leadership", "ego"],
        "reflection": "The most powerful giving is the kind that expects nothing in return.",
        "is_scripture": False,
    },
    {
        "master": "Hafiz",
        "tradition": "Sufi / Persian",
        "era": "1325–1390",
        "quote": "I have come to drag you out of yourself and take you in my heart. I have come to bring out the beauty you never knew you had.",
        "source": "Divan-e Hafiz",
        "themes": ["love", "self-knowledge", "consciousness", "relationships"],
        "reflection": "The greatest leaders see potential in others that others cannot yet see in themselves.",
        "is_scripture": False,
    },
    {
        "master": "Hafiz",
        "tradition": "Sufi / Persian",
        "era": "1325–1390",
        "quote": "Fear is the cheapest room in the house. I would like to see you living in better conditions.",
        "source": "The Gift (Ladinsky translation)",
        "themes": ["courage", "adversity", "self-knowledge", "purpose"],
        "reflection": "Fear is real — but it is the smallest room you can choose to live in.",
        "is_scripture": False,
    },
    # ── Laozi / Tao Te Ching ──────────────────────────────────────────────────
    {
        "master": "Laozi",
        "tradition": "Taoist",
        "era": "~6th century BCE",
        "quote": "A leader is best when people barely know he exists. When his work is done, his aim fulfilled, they will say: we did it ourselves.",
        "source": "Tao Te Ching, Chapter 17",
        "themes": ["leadership", "ego", "service", "work"],
        "reflection": "The highest form of leadership leaves no fingerprints.",
        "is_scripture": False,
    },
    {
        "master": "Laozi",
        "tradition": "Taoist",
        "era": "~6th century BCE",
        "quote": "Knowing others is intelligence; knowing yourself is true wisdom. Mastering others is strength; mastering yourself is true power.",
        "source": "Tao Te Ching, Chapter 33",
        "themes": ["self-knowledge", "leadership", "wisdom", "discipline"],
        "reflection": "External mastery follows internal mastery — never the reverse.",
        "is_scripture": False,
    },
    {
        "master": "Laozi",
        "tradition": "Taoist",
        "era": "~6th century BCE",
        "quote": "The journey of a thousand miles begins with a single step.",
        "source": "Tao Te Ching, Chapter 64",
        "themes": ["discipline", "courage", "purpose", "work"],
        "reflection": "Paralysis comes from looking at the destination. Movement comes from taking the next step.",
        "is_scripture": False,
    },
    {
        "master": "Laozi",
        "tradition": "Taoist",
        "era": "~6th century BCE",
        "quote": "Nature does not hurry, yet everything is accomplished.",
        "source": "Tao Te Ching",
        "themes": ["equanimity", "work", "leadership", "surrender"],
        "reflection": "Urgency without presence is noise. Depth without speed is power.",
        "is_scripture": False,
    },
    {
        "master": "Laozi",
        "tradition": "Taoist",
        "era": "~6th century BCE",
        "quote": "Respond intelligently even to unintelligent treatment.",
        "source": "Tao Te Ching",
        "themes": ["relationships", "leadership", "equanimity", "discipline"],
        "reflection": "The quality of your response tells more about you than the quality of the provocation.",
        "is_scripture": False,
    },
    # ── Zhuangzi ──────────────────────────────────────────────────────────────
    {
        "master": "Zhuangzi",
        "tradition": "Taoist",
        "era": "~4th century BCE",
        "quote": "Cherish that which is within you, and shut off that which is without; for much knowledge is a curse.",
        "source": "Zhuangzi",
        "themes": ["self-knowledge", "wisdom", "mind", "consciousness"],
        "reflection": "At some point, more information stops helping — deeper reflection begins.",
        "is_scripture": False,
    },
    {
        "master": "Zhuangzi",
        "tradition": "Taoist",
        "era": "~4th century BCE",
        "quote": "Flow with whatever may happen and let your mind be free. Stay centered by accepting whatever you are doing. This is the ultimate.",
        "source": "Zhuangzi",
        "themes": ["equanimity", "surrender", "mind", "discipline"],
        "reflection": "Resistance to what is creates more suffering than what is.",
        "is_scripture": False,
    },
    # ── Marcus Aurelius ────────────────────────────────────────────────────────
    {
        "master": "Marcus Aurelius",
        "tradition": "Stoic",
        "era": "121–180 CE",
        "quote": "You have power over your mind — not outside events. Realize this, and you will find strength.",
        "source": "Meditations",
        "themes": ["mind", "equanimity", "adversity", "leadership"],
        "reflection": "The only domain of absolute sovereignty is your own response.",
        "is_scripture": False,
    },
    {
        "master": "Marcus Aurelius",
        "tradition": "Stoic",
        "era": "121–180 CE",
        "quote": "Waste no more time arguing about what a good man should be. Be one.",
        "source": "Meditations, Book 10",
        "themes": ["discipline", "leadership", "truth", "work"],
        "reflection": "The conversation about values is cheap. Living them is the point.",
        "is_scripture": False,
    },
    {
        "master": "Marcus Aurelius",
        "tradition": "Stoic",
        "era": "121–180 CE",
        "quote": "The impediment to action advances action. What stands in the way becomes the way.",
        "source": "Meditations, Book 5",
        "themes": ["adversity", "courage", "leadership", "discipline"],
        "reflection": "Every obstacle contains within it the energy needed to move past it.",
        "is_scripture": False,
    },
    {
        "master": "Marcus Aurelius",
        "tradition": "Stoic",
        "era": "121–180 CE",
        "quote": "Loss is nothing else but change, and change is nature's delight.",
        "source": "Meditations",
        "themes": ["impermanence", "adversity", "equanimity", "surrender"],
        "reflection": "What we call loss, the universe calls transformation.",
        "is_scripture": False,
    },
    {
        "master": "Marcus Aurelius",
        "tradition": "Stoic",
        "era": "121–180 CE",
        "quote": "Do not indulge in dreams of what you do not have, but reckon up the chief of the blessings you do have, and then thankfully remember how eagerly you would have sought them if they were not yours.",
        "source": "Meditations",
        "themes": ["gratitude", "equanimity", "mind", "purpose"],
        "reflection": "Gratitude is a discipline — it requires choosing to see what is already present.",
        "is_scripture": False,
    },
    # ── Epictetus ─────────────────────────────────────────────────────────────
    {
        "master": "Epictetus",
        "tradition": "Stoic",
        "era": "50–135 CE",
        "quote": "Make the best use of what is in your power, and take the rest as it happens.",
        "source": "Enchiridion",
        "themes": ["equanimity", "discipline", "adversity", "leadership"],
        "reflection": "Precision about what is in your control is the beginning of peace.",
        "is_scripture": False,
    },
    {
        "master": "Epictetus",
        "tradition": "Stoic",
        "era": "50–135 CE",
        "quote": "Seek not that the things which happen should happen as you wish; but wish the things which happen to be as they are, and you will have a tranquil flow of life.",
        "source": "Enchiridion",
        "themes": ["surrender", "equanimity", "mind", "impermanence"],
        "reflection": "The root of suffering is the gap between what is and what we insist it should be.",
        "is_scripture": False,
    },
    {
        "master": "Epictetus",
        "tradition": "Stoic",
        "era": "50–135 CE",
        "quote": "We cannot choose our external circumstances, but we can always choose how we respond to them.",
        "source": "Enchiridion",
        "themes": ["adversity", "leadership", "mind", "discipline"],
        "reflection": "Between stimulus and response is a space. Your entire character lives in that space.",
        "is_scripture": False,
    },
    # ── Khalil Gibran ─────────────────────────────────────────────────────────
    {
        "master": "Khalil Gibran",
        "tradition": "Universal / Mystical",
        "era": "1883–1931",
        "quote": "Your work is to discover your world and then with all your heart give yourself to it.",
        "source": "The Prophet",
        "themes": ["purpose", "work", "discipline", "love"],
        "reflection": "Discovery and devotion — these two acts, taken together, are a life well-lived.",
        "is_scripture": False,
    },
    {
        "master": "Khalil Gibran",
        "tradition": "Universal / Mystical",
        "era": "1883–1931",
        "quote": "Your pain is the breaking of the shell that encloses your understanding.",
        "source": "The Prophet",
        "themes": ["suffering", "adversity", "wisdom", "consciousness"],
        "reflection": "Pain is not punishment. It is the price of becoming more.",
        "is_scripture": False,
    },
    {
        "master": "Khalil Gibran",
        "tradition": "Universal / Mystical",
        "era": "1883–1931",
        "quote": "The most pitiful among men is he who turns his dreams into silver and gold.",
        "source": "The Prophet",
        "themes": ["purpose", "ego", "truth", "work"],
        "reflection": "When you monetize everything, you eventually lose the thing that made it worth doing.",
        "is_scripture": False,
    },
    {
        "master": "Khalil Gibran",
        "tradition": "Universal / Mystical",
        "era": "1883–1931",
        "quote": "And in the sweetness of friendship let there be laughter, and sharing of pleasures. For in the dew of little things the heart finds its morning and is refreshed.",
        "source": "The Prophet",
        "themes": ["relationships", "love", "gratitude", "equanimity"],
        "reflection": "The small moments of genuine connection are the architecture of a meaningful life.",
        "is_scripture": False,
    },
    {
        "master": "Khalil Gibran",
        "tradition": "Universal / Mystical",
        "era": "1883–1931",
        "quote": "You talk when you cease to be at peace with your thoughts.",
        "source": "The Prophet",
        "themes": ["mind", "truth", "wisdom", "self-knowledge"],
        "reflection": "Speech fills the silence that discomfort creates. Inner peace needs less filling.",
        "is_scripture": False,
    },
    # ── Modern Strategy / Entrepreneurship ────────────────────────────────────
    {
        "master": "Naval Ravikant",
        "tradition": "Modern Strategy",
        "era": "21st century",
        "quote": "Productize yourself. If you can be easily replaced, you will be. Find what you are the best in the world at, and keep doing it until you are.",
        "source": "The Almanack of Naval Ravikant",
        "themes": ["work", "purpose", "leadership", "discipline"],
        "reflection": "Leverage comes from being distinct. Don't compete — create a category of one.",
        "is_scripture": False,
    },
    {
        "master": "Naval Ravikant",
        "tradition": "Modern Strategy",
        "era": "21st century",
        "quote": "Earn with your mind, not your time. All the real wealth in life comes from compound interest in relationships, money, and habits.",
        "source": "The Almanack of Naval Ravikant",
        "themes": ["work", "discipline", "wisdom", "relationships"],
        "reflection": "Linear effort yields linear results. Compounding yields the future.",
        "is_scripture": False,
    },
    {
        "master": "Charlie Munger",
        "tradition": "Modern Strategy",
        "era": "20th–21st century",
        "quote": "Invert, always invert. Turn a situation or problem upside down. Look at it backward. What happens if all our plans go wrong? Where don't we want to go, and how do you get there? Instead of looking for success, make a list of how to fail.",
        "source": "Poor Charlie's Almanack",
        "themes": ["wisdom", "discipline", "mind", "leadership"],
        "reflection": "Avoiding stupidity is easier than seeking brilliance. Start by removing the obstacles.",
        "is_scripture": False,
    },
    {
        "master": "Charlie Munger",
        "tradition": "Modern Strategy",
        "era": "20th–21st century",
        "quote": "The best thing a human can do is to help another human being know more. A life properly lived is just learn, learn, learn all the time.",
        "source": "Poor Charlie's Almanack",
        "themes": ["service", "wisdom", "purpose", "work"],
        "reflection": "Continuous learning is the only durable competitive advantage.",
        "is_scripture": False,
    },
]

# ── Seed ──────────────────────────────────────────────────────────────────────

def seed_wisdom_corpus(db: Session) -> int:
    """Insert all corpus entries if the table is empty. Returns count inserted."""
    existing = db.query(SpiritualWisdom).count()
    if existing >= len(CORPUS):
        return 0
    inserted = 0
    existing_quotes = {
        r.quote[:60] for r in db.query(SpiritualWisdom.quote).all()
    }
    for entry in CORPUS:
        if entry["quote"][:60] in existing_quotes:
            continue
        w = SpiritualWisdom(
            master=entry["master"],
            tradition=entry["tradition"],
            era=entry.get("era", ""),
            quote=entry["quote"],
            source=entry.get("source", ""),
            themes=entry.get("themes", []),
            reflection=entry.get("reflection", ""),
            is_scripture=entry.get("is_scripture", False),
        )
        db.add(w)
        inserted += 1
    db.commit()
    return inserted

# ── Contextual wisdom picker ───────────────────────────────────────────────────

_THEME_MAP: dict[str, list[str]] = {
    "low_energy":        ["suffering", "adversity", "equanimity", "courage", "impermanence"],
    "high_stress":       ["equanimity", "surrender", "mind", "impermanence", "adversity"],
    "leadership":        ["leadership", "service", "ego", "work", "truth"],
    "relationships":     ["relationships", "love", "ego", "truth", "service"],
    "purpose":           ["purpose", "consciousness", "self-knowledge", "wisdom", "truth"],
    "gratitude":         ["gratitude", "love", "equanimity", "impermanence"],
    "default":           ["wisdom", "discipline", "self-knowledge", "purpose", "leadership"],
}


def get_contextual_wisdom(user_id: str, db: Session) -> SpiritualWisdom | None:
    """
    Return one wisdom entry whose themes best match the user's current state.
    Selection is deterministic per day (same entry all day) but rotates daily.
    """
    # Determine user context from recent check-ins
    recent = (
        db.query(DailyCheckIn)
        .filter(DailyCheckIn.user_id == user_id)
        .order_by(DailyCheckIn.check_in_date.desc())
        .limit(3)
        .all()
    )

    category = "default"
    if recent:
        avg_energy = sum(c.energy for c in recent) / len(recent)
        avg_stress = sum(c.stress for c in recent) / len(recent)
        if avg_energy < 4.5:
            category = "low_energy"
        elif avg_stress > 6.5:
            category = "high_stress"

    # Also factor in user profile themes
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile and category == "default":
        stressors = " ".join(profile.current_stressors or []).lower()
        if "relationship" in stressors or "team" in stressors or "conflict" in stressors:
            category = "relationships"
        elif "purpose" in stressors or "direction" in stressors or "meaning" in stressors:
            category = "purpose"

    target_themes = _THEME_MAP.get(category, _THEME_MAP["default"])

    # Score each wisdom entry by theme overlap
    all_wisdom = db.query(SpiritualWisdom).filter(SpiritualWisdom.active == True).all()
    if not all_wisdom:
        return None

    scored = []
    user_prefs = profile.wisdom_preferences if profile else []
    
    for w in all_wisdom:
        overlap = len(set(w.themes) & set(target_themes))
        
        # Boost entries that match user tradition preferences
        if user_prefs and w.tradition in user_prefs:
            overlap += 5  # Strong preference weight
            
        scored.append((overlap, w))

    scored.sort(key=lambda x: x[0], reverse=True)

    # From the top-scoring group, pick deterministically by date so it's stable all day
    top_score = scored[0][0]
    top_group = [w for score, w in scored if score == top_score]
    day_seed = int(date.today().strftime("%Y%m%d")) + hash(user_id) % 1000
    chosen = top_group[day_seed % len(top_group)]
    return chosen


# ── Ask the Masters ────────────────────────────────────────────────────────────

def _pick_relevant_entries(question: str, all_wisdom: list[SpiritualWisdom], n: int = 10) -> list[SpiritualWisdom]:
    """Simple keyword-based relevance scoring to select corpus entries for the AI context."""
    q_lower = question.lower()

    # Theme keywords
    keyword_theme_map = {
        "leader": ["leadership", "service", "ego"],
        "lead": ["leadership", "service", "ego"],
        "boss": ["leadership", "relationships"],
        "team": ["leadership", "relationships", "service"],
        "decision": ["wisdom", "truth", "leadership"],
        "choose": ["wisdom", "truth", "purpose"],
        "stress": ["equanimity", "adversity", "mind"],
        "anxious": ["equanimity", "mind", "surrender"],
        "afraid": ["courage", "adversity", "self-knowledge"],
        "fear": ["courage", "adversity", "self-knowledge"],
        "fail": ["adversity", "discipline", "courage"],
        "angry": ["equanimity", "relationships", "mind"],
        "conflict": ["relationships", "truth", "ego"],
        "ego": ["ego", "self-knowledge", "consciousness"],
        "purpose": ["purpose", "consciousness", "wisdom"],
        "meaning": ["purpose", "consciousness", "truth"],
        "love": ["love", "relationships", "service"],
        "relationship": ["relationships", "love", "ego"],
        "mind": ["mind", "discipline", "consciousness"],
        "peace": ["equanimity", "surrender", "mind"],
        "work": ["work", "discipline", "service"],
        "success": ["discipline", "work", "purpose"],
        "suffer": ["suffering", "adversity", "impermanence"],
        "pain": ["suffering", "adversity", "wisdom"],
        "grateful": ["gratitude", "love", "equanimity"],
        "disciplin": ["discipline", "work", "mind"],
        "focus": ["discipline", "mind", "work"],
        "truth": ["truth", "self-knowledge", "wisdom"],
        "honest": ["truth", "relationships", "leadership"],
        "change": ["impermanence", "discipline", "courage"],
        "let go": ["surrender", "impermanence", "equanimity"],
        "service": ["service", "love", "leadership"],
        "god": ["consciousness", "surrender", "truth"],
        "spiritual": ["consciousness", "truth", "self-knowledge"],
    }

    relevant_themes: set[str] = set()
    for kw, themes in keyword_theme_map.items():
        if kw in q_lower:
            relevant_themes.update(themes)

    if not relevant_themes:
        relevant_themes = {"wisdom", "leadership", "self-knowledge", "purpose"}

    scored = []
    for w in all_wisdom:
        score = len(set(w.themes) & relevant_themes)
        scored.append((score, w))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [w for _, w in scored[:n]]

    # Ensure diversity — at most 2 from the same master
    seen_masters: dict[str, int] = {}
    diverse: list[SpiritualWisdom] = []
    for w in selected:
        count = seen_masters.get(w.master, 0)
        if count < 2:
            diverse.append(w)
            seen_masters[w.master] = count + 1
        if len(diverse) >= 8:
            break

    return diverse


async def ask_masters(question: str, user_id: str, db: Session) -> dict:
    """
    Given a question, pick relevant corpus entries and ask the AI to synthesize
    a unified response in the voice of the spiritual tradition, with citations.

    Returns:
        {
          "synthesis": str,        — the unified wisdom response
          "citations": [           — masters drawn from
            {"master": str, "tradition": str, "quote": str, "source": str}
          ],
          "theme": str             — dominant theme identified
        }
    """
    all_wisdom = db.query(SpiritualWisdom).filter(SpiritualWisdom.active == True).all()
    if not all_wisdom:
        return {"synthesis": "The corpus of wisdom is still being gathered.", "citations": [], "theme": "wisdom"}

    entries = _pick_relevant_entries(question, all_wisdom, n=10)

    # Build corpus text for the AI
    corpus_lines = []
    for w in entries:
        corpus_lines.append(
            f'[{w.master} — {w.source}]\n"{w.quote}"\nReflection: {w.reflection}'
        )
    corpus_text = "\n\n".join(corpus_lines)

    # Get user profile for personalization
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    user_context = ""
    if profile:
        user_context = (
            f"The person asking is {profile.full_name}, a {profile.role}"
            + (f" at {profile.organization}" if profile.organization else "")
            + (f". Their biggest challenge: {profile.biggest_challenge}" if profile.biggest_challenge else "")
            + "."
        )

    system_prompt = (
        "You are a synthesis of humanity's greatest spiritual wisdom traditions — "
        "Hindu, Buddhist, Sufi, Taoist, Stoic, Christian, Islamic, Jain, and more. "
        "When someone brings you a question, you draw from the actual teachings of the masters "
        "provided to you, synthesize a unified response, and cite your sources. "
        "\n\nRules:"
        "\n- Write in a calm, direct, deeply insightful tone. Not preachy. Not vague."
        "\n- Synthesize — do NOT just list what each master said separately."
        "\n- Weave the wisdom together into one cohesive, practical response."
        "\n- Be specific to the person's actual situation."
        "\n- Response length: 150–250 words."
        "\n- End with 2–4 specific masters you drew from, with their exact quote used."
        "\n\nReturn strict JSON: "
        '{"synthesis": str, "citations": [{"master": str, "tradition": str, "quote": str, "source": str}], "theme": str}'
    )

    user_prompt = (
        f"{user_context}\n\nQuestion: {question}\n\n"
        f"Relevant wisdom from the corpus:\n\n{corpus_text}\n\n"
        "Synthesize a response. Return JSON only."
    )

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        # Fallback: return the top entry with a note
        top = entries[0] if entries else None
        if top:
            return {
                "synthesis": f"{top.reflection}\n\nAs {top.master} wrote: \"{top.quote}\"",
                "citations": [{"master": top.master, "tradition": top.tradition, "quote": top.quote, "source": top.source}],
                "theme": top.themes[0] if top.themes else "wisdom",
            }
        return {"synthesis": "The masters are silent today. Sit with the question itself.", "citations": [], "theme": "wisdom"}

    model = os.getenv("OPENAI_COACH_MODEL", "gpt-4o-mini").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    body = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_output_tokens": 600,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(f"{base_url}/responses", headers=headers, json=body)
            resp.raise_for_status()
            raw = resp.json()

        # Extract text from response
        text = ""
        output = raw.get("output", [])
        for item in output:
            content = item.get("content", [])
            for c in content:
                if isinstance(c, dict) and c.get("text"):
                    text += c["text"]
        if not text:
            text = raw.get("output_text", "")

        # Parse JSON
        text = text.strip()
        if text.startswith("```"):
            import re
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)

        data = json.loads(text)
        return {
            "synthesis": data.get("synthesis", ""),
            "citations": data.get("citations", []),
            "theme": data.get("theme", "wisdom"),
        }

    except Exception as e:
        # Return best fallback from corpus
        if entries:
            top = entries[0]
            return {
                "synthesis": f"{top.reflection}\n\nAs {top.master} taught: \"{top.quote}\"\n\n— {top.source}",
                "citations": [{"master": top.master, "tradition": top.tradition, "quote": top.quote, "source": top.source}],
                "theme": top.themes[0] if top.themes else "wisdom",
            }
        return {"synthesis": "Seek the answer in silence — sometimes that is the masters speaking.", "citations": [], "theme": "wisdom"}
