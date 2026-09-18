"""Chenkron Asistan — uygulama içi yapay zekâ.

    config.py   model adı ve anahtar (secrets.py git'e girmez, derlemeye girer)
    gemini.py   Gemini REST istemcisi (araç çağrısı destekli)
    tools.py    araç tanımları + sistem bilgisi (uygulama nasıl kullanılır)
    actions.py  araçların uygulamadaki karşılığı (GUI iş parçacığında koşar)
    agent.py    sohbet döngüsü: soru -> model -> araçlar -> cevap
    widget.py   daire düğme, morph animasyonu, hap giriş kutusu, cevap balonu
"""
