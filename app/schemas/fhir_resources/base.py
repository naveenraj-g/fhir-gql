"""DomainResource: the elements every FHIR resource carries (generated, do not edit by hand)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.fhir_datatypes import Code, Extension, Id, Meta, Narrative, Uri


class DomainResource(BaseModel):
    "A resource that carries narrative, extensions and contained resources."

    # `extra=ignore`: the validated raw body, not these models, is what gets stored, so an element
    # a model does not declare is never lost.
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: Id | None = Field(
        None,
        description="The logical id of the resource, as used in the URL for the resource. Once assigned, this value never changes."
        + " Server-managed: assigned from the resource's public id sequence; ignored if sent.",
    )
    meta: Meta | None = Field(
        None,
        description="The metadata about the resource. This is content that is maintained by the infrastructure. Changes to the content might not always be associated with version changes to the resource."
        + " Server-managed: stamped on at read time; ignored if sent.",
    )
    implicitRules: Uri | None = Field(
        None,
        description="A reference to a set of rules that were followed when the resource was constructed, and which must be understood when processing the content. Often, this is a reference to an implementation guide that defines the special rules along with other profiles etc.",
    )
    language: Code | None = Field(
        None, description="The base language in which the resource is written."
    )
    text: Narrative | None = Field(
        None,
        description='A human-readable narrative that contains a summary of the resource and can be used to represent the content of the resource to a human. The narrative need not encode all the structured data, but is required to contain sufficient detail to make it "clinically safe" for a human to just read the narrative. Resource definitions may define what content should be represented in the narrative to ensure clinical safety.',
    )
    contained: list[dict] | None = Field(
        None,
        description="These resources do not have an independent existence apart from the resource that contains them - they cannot be identified independently, and nor can they have their own independent transaction scope.",
    )
    extension: list[Extension] | None = Field(
        None,
        description="May be used to represent additional information that is not part of the basic definition of the resource. To make the use of extensions safe and manageable, there is a strict set of governance  applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension.",
    )
    modifierExtension: list[Extension] | None = Field(
        None,
        description="May be used to represent additional information that is not part of the basic definition of the resource and that modifies the understanding of the element that contains it and/or the understanding of the containing element's descendants. Usually modifier elements provide negation or qualification. To make the use of extensions safe and manageable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer is allowed to define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension. Applications processing a resource are required to check for modifier extensions.\n\nModifier extensions SHALL NOT change the meaning of any elements on Resource or DomainResource (including cannot change the meaning of modifierExtension itself).",
    )
