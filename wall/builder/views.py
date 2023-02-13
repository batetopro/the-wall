from rest_framework.views import APIView
from rest_framework.response import Response

from .builder import History


class ProfileIceAmountPerDay(APIView):
    def get(self, request, profile, day):
        """
        How much ice was added to a profile on a given day.
        """
        return Response({"day": day, "ice_amount": History.amount_per_profile_per_day(profile, day)})


class ProfilePricePerDay(APIView):
    def get(self, request, profile, day):
        """
        How much did the build of a profile costed on a given day.
        """
        return Response({"day": day, "cost": History.price_per_profile_per_day(profile, day)})


class PricePerDay(APIView):
    def get(self, request, day):
        """
        How much the build of all profiles costed om a given day.
        """
        return Response({"day": day, "cost": History.price_per_day(day)})


class PriceTotal(APIView):
    def get(self, request):
        """
        How much cost the build of all profiles.
        """
        return Response({"day": None, "cost": History.overall()})
