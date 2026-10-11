from django.contrib import admin
from .models import (
    VCProfile, VCPreference, StartupProfile, PitchDeck, IRDeck,
    PortfolioDocument, Recommendation, Bookmark, Like, Match, AIReport,
    MatchResult, Notification, CoffeeChat,
)

for m in (VCProfile, VCPreference, StartupProfile, PitchDeck, IRDeck,
          PortfolioDocument, Recommendation, Bookmark, Like, Match, AIReport,
          MatchResult, Notification, CoffeeChat):
    admin.site.register(m)
